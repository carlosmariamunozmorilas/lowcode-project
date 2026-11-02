"""Running components of a client's growth system and their monthly record.

A month is append-only; a correction is a new row that supersedes the old one.
Nobody types a benefit the app can compute: for holdout_kept and pilot_estimate
components the app fills it in. An invoice month is recorded only by an
assigned lead who neither requested nor owned the origin action.
"""

import re
import sqlite3

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import lifecycle
import measure
import roi
from auth import actor, eligible_lead_ids, get_client, login_required
from db import get_db, transaction
from routes.actions import to_action

bp = Blueprint("components", __name__)


def get_component(component_id: int, *, write: bool = False):
    component = get_db().execute(
        "SELECT * FROM components WHERE id = ?", (component_id,)).fetchone()
    if component is None:
        abort(404)
    get_client(component["client_id"], write=write)
    return component


def number(form, name, default=0.0):
    raw = form.get(name, "").strip()
    if raw == "":
        return default
    value = float(raw)
    if value != value or value < 0 or value == float("inf"):
        raise ValueError(f"{name.replace('_', ' ')} must be a number of zero or more")
    return value


@bp.route("/components/<int:component_id>")
@login_required
def show(component_id):
    component = get_component(component_id)
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id = ?",
                          (component["client_id"],)).fetchone()
    rate = client["hourly_rate_eur"]
    months = conn.execute(
        """SELECT cm.*, u.full_name AS recorder,
                  EXISTS (SELECT 1 FROM component_months n WHERE n.supersedes_id = cm.id)
                      AS superseded
           FROM component_months cm JOIN users u ON u.id = cm.recorded_by
           WHERE component_id = ? ORDER BY month, cm.id""", (component_id,)).fetchall()
    rows = []
    for m in months:
        cost = roi.component_month_cost(m["operating_cost_eur"], m["operating_hours"], rate)
        rows.append({"m": m, "cost": cost,
                     "roi": roi.continuation_roi(m["measured_benefit_eur"], cost)})
    origin = (conn.execute("SELECT * FROM actions WHERE id = ?",
                           (component["origin_action_id"],)).fetchone()
              if component["origin_action_id"] else None)
    may_invoice = lifecycle.may_record_invoice_month(
        actor(), to_action(origin) if origin else None, eligible_lead_ids(component["client_id"]))
    return render_template("component.html", component=component, client=client, rows=rows,
                           origin=origin, may_invoice=may_invoice)


@bp.route("/components/<int:component_id>/months", methods=["POST"])
@login_required
def record_month(component_id):
    component = get_component(component_id, write=True)
    conn = get_db()
    form = request.form
    month = form.get("month", "")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        flash("Refused: the month must look like 2026-10.", "error")
        return redirect(url_for("components.show", component_id=component_id))
    origin = (conn.execute("SELECT * FROM actions WHERE id = ?",
                           (component["origin_action_id"],)).fetchone()
              if component["origin_action_id"] else None)
    try:
        cost = number(form, "operating_cost_eur")
        hours = number(form, "operating_hours")
        runs = form.get("runs", type=int)
        failed = form.get("failed_runs", type=int)
        freed = number(form, "hours_freed", None)
        if component["measurement"] == "invoice":
            if not lifecycle.may_record_invoice_month(
                    actor(), to_action(origin) if origin else None,
                    eligible_lead_ids(component["client_id"])):
                raise lifecycle.TransitionError(
                    "an invoice month is recorded by an assigned lead who neither requested "
                    "nor owned the original action")
            benefit, confidence = number(form, "measured_benefit_eur", None), "documented"
            if benefit is None:
                raise ValueError("an invoice month needs the amount the invoices show")
        else:
            # Whatever was typed is ignored: the app computes this figure.
            benefit, confidence = measure.component_benefit_for_month(conn, component, month)
        supersedes = form.get("supersedes_id", type=int)
        if supersedes is not None:
            old = conn.execute(
                """SELECT * FROM component_months WHERE id = ? AND component_id = ?
                   AND month = ? AND NOT EXISTS (SELECT 1 FROM component_months n
                                                 WHERE n.supersedes_id = component_months.id)""",
                (supersedes, component_id, month)).fetchone()
            if old is None:
                raise ValueError("a correction must replace this component's current row for "
                                 "the same month")
        else:
            existing = conn.execute(
                "SELECT 1 FROM component_months WHERE component_id = ? AND month = ?",
                (component_id, month)).fetchone()
            if existing:
                raise ValueError("this month is already recorded; record a correction instead")
        # Each benefit is counted once: when another component already carries
        # this benefit for the month, this one records its cost and hours only.
        # (Found by the 2 November code review: refusing the whole month lost
        # the cost.)
        shared = benefit is not None and component["benefit_key"] and conn.execute(
            """SELECT 1 FROM component_months cm
               WHERE cm.client_id = ? AND cm.month = ? AND cm.benefit_key = ?
                 AND cm.measured_benefit_eur IS NOT NULL AND cm.component_id <> ?
                 AND NOT EXISTS (SELECT 1 FROM component_months n WHERE n.supersedes_id = cm.id)""",
            (component["client_id"], month, component["benefit_key"], component_id)).fetchone()
        if shared:
            benefit, confidence = None, None
        with transaction(conn):
            conn.execute(
                """INSERT INTO component_months (component_id, client_id, month,
                       operating_cost_eur, operating_hours, measured_benefit_eur, confidence,
                       benefit_key, runs, failed_runs, hours_freed, supersedes_id, recorded_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (component_id, component["client_id"], month, cost, hours, benefit, confidence,
                 component["benefit_key"], runs, failed, freed, supersedes, g.user["id"]))
    except sqlite3.IntegrityError:
        flash("Refused: another component already carries this benefit for this month — "
              "each benefit is counted once.", "error")
    except (ValueError, lifecycle.TransitionError) as error:
        flash(f"Refused: {error}", "error")
    else:
        if shared:
            flash("Month recorded with cost and hours only: another component already "
                  "carries this benefit for the month, and each benefit is counted once.",
                  "success")
        else:
            flash("Month recorded.", "success")
    return redirect(url_for("components.show", component_id=component_id))


@bp.route("/components/<int:component_id>/status", methods=["POST"])
@login_required
def set_status(component_id):
    component = get_component(component_id, write=True)
    if g.user["id"] not in eligible_lead_ids(component["client_id"]):
        abort(403, "Only an assigned lead keeps, reviews or retires a component.")
    status = request.form.get("status")
    if status not in {"running", "review_due", "retired"}:
        abort(400)
    conn = get_db()
    with transaction(conn):
        conn.execute(
            # A component brought back from retirement has no retirement date.
            "UPDATE components SET status = ?, retired_on = CASE WHEN ? = 'retired' "
            "THEN date('now') ELSE NULL END WHERE id = ?",
            (status, status, component_id))
    flash("Status updated.", "success")
    return redirect(url_for("components.show", component_id=component_id))
