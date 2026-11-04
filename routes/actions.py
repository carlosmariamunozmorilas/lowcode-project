"""Actions: create, edit before review, and move through the workflow (spec v2 §5).

Every stage change goes through lifecycle.check_transition and is written
together with its action_history row in one transaction. Fields the workflow
owns (status, measured result, decision) are never read from an edit form.
"""

import sqlite3
from dataclasses import replace

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import lifecycle
import measure
import roi
from auth import actor, assigned_people, eligible_lead_ids, get_client, login_required, today
from db import get_db, transaction

bp = Blueprint("actions", __name__)

TEXT_FIELDS = ("title", "hypothesis", "primary_metric", "lifecycle_stage", "benefit_type",
               "comparison", "scope_channel", "window_start", "window_end", "benefit_key",
               "discipline")
MONEY_FIELDS = ("expected_benefit_eur", "setup_cost_eur", "setup_hours", "operating_cost_eur",
                "operating_hours", "hurdle_eur")
INT_FIELDS = ("post_period_days",)
NOT_NULL_NUMBERS = {"setup_cost_eur", "setup_hours", "operating_cost_eur", "operating_hours",
                    "hurdle_eur"}
DISCIPLINES = ("ecommerce", "digital_marketing", "performance_marketing", "digital_growth",
               "agentic_ai", "automations")
DEFAULT_COMPARISON = {"contribution": "before_after", "avoided_cost": "invoice",
                      "enabler": "none"}


class FormError(ValueError):
    pass


def to_action(row: sqlite3.Row, **changes) -> lifecycle.Action:
    names = lifecycle.Action.__dataclass_fields__
    action = lifecycle.Action(**{k: row[k] for k in names if k in row.keys()})
    return replace(action, **changes) if changes else action


def get_action(action_id: int, *, write: bool = False) -> sqlite3.Row:
    action = get_db().execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    if action is None:
        abort(404)
    get_client(action["client_id"], write=write)
    return action


def read_form(form) -> dict:
    """The editable fields only. Anything else posted — a status, a result, a
    decision — is ignored, never written (the mass-assignment test)."""
    values = {}
    for name in TEXT_FIELDS:
        if name in form:
            values[name] = form.get(name, "").strip() or None
    for name in MONEY_FIELDS + INT_FIELDS:
        if name not in form:
            continue
        raw = form.get(name, "").strip()
        if raw == "":
            values[name] = 0.0 if name in NOT_NULL_NUMBERS else None
            continue
        try:
            number = int(raw) if name in INT_FIELDS else float(raw)
        except ValueError:
            raise FormError(f"{name.replace('_', ' ')} must be a number") from None
        if number != number or number in (float("inf"), float("-inf")):
            raise FormError(f"{name.replace('_', ' ')} must be a finite number")
        if number < 0 and name != "expected_benefit_eur":
            raise FormError(f"{name.replace('_', ' ')} cannot be negative")
        values[name] = number
    if values.get("discipline") and values["discipline"] not in DISCIPLINES:
        raise FormError("unknown discipline")
    if values.get("primary_metric") and values["primary_metric"] not in lifecycle.METRICS:
        raise FormError("the primary metric must come from the vocabulary")
    if values.get("lifecycle_stage") and values["lifecycle_stage"] not in lifecycle.LIFECYCLE_STAGES:
        raise FormError("unknown lifecycle stage")
    if values.get("benefit_type") and values["benefit_type"] not in lifecycle.BENEFIT_TYPES:
        raise FormError("unknown benefit type")
    if not values.get("title", "x"):
        raise FormError("an action needs a title")
    return values


def check_scope(client_id: int, scope_channel: str | None, comparison: str | None) -> None:
    """A channel scope must be one of the client's channels, and needs before/after (D1)."""
    if not scope_channel:
        return
    if scope_channel not in measure.client_channels(get_db(), client_id):
        raise FormError("the channel scope must be one of this client's channels")
    if comparison != "before_after":
        raise FormError("a channel scope works only with a before/after comparison")


def form_choices(client_id: int) -> dict:
    return {
        "people": assigned_people(client_id),
        "metrics": sorted(lifecycle.METRICS),
        "stages": sorted(lifecycle.LIFECYCLE_STAGES),
        "disciplines": DISCIPLINES,
        "benefit_types": sorted(lifecycle.BENEFIT_TYPES),
        "comparisons": lifecycle.COMPARISONS_FOR,
        "channels": measure.client_channels(get_db(), client_id),
    }


def record(conn, action_id: int, from_status: str | None, to_status: str, note: str = "") -> None:
    conn.execute(
        """INSERT INTO action_history (action_id, from_status, to_status, actor_id, note)
           VALUES (?, ?, ?, ?, ?)""",
        (action_id, from_status, to_status, g.user["id"], note or None),
    )


@bp.route("/clients/<int:client_id>/actions/new", methods=["GET", "POST"])
@login_required
def new(client_id):
    client = get_client(client_id, write=True)
    conn = get_db()
    plan = None
    plan_id = request.values.get("plan", type=int)
    if plan_id:
        plan = conn.execute("SELECT * FROM plan_templates WHERE id = ?", (plan_id,)).fetchone()
        if plan is None or not plan["featured"]:
            flash("Only the six featured plans can start an action in the MVP.", "error")
            return redirect(url_for("clients.plans", client_id=client_id))

    if request.method == "POST":
        try:
            values = read_form(request.form)
            if not values.get("title"):
                raise FormError("an action needs a title")
            values.setdefault("benefit_type", plan["benefit_type"] if plan else "contribution")
            values.setdefault("discipline", plan["discipline"] if plan else "digital_growth")
            values["discipline"] = values["discipline"] or (plan["discipline"] if plan
                                                            else "digital_growth")
            values["benefit_type"] = values["benefit_type"] or "contribution"
            if values.get("comparison") not in lifecycle.COMPARISONS_FOR[values["benefit_type"]]:
                values["comparison"] = DEFAULT_COMPARISON[values["benefit_type"]]
            check_scope(client_id, values.get("scope_channel"), values["comparison"])
            columns = {**values, "client_id": client_id, "requester_id": g.user["id"],
                       "plan_template_id": plan["id"] if plan else None, "status": "submitted"}
            with transaction(conn):
                cur = conn.execute(
                    f"INSERT INTO actions ({', '.join(columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})", tuple(columns.values()))
                record(conn, cur.lastrowid, None, "submitted")
        except (FormError, sqlite3.IntegrityError) as error:
            flash(f"Not saved: {error}", "error")
            return render_template("action_form.html", client=client, plan=plan,
                                   action=request.form, editing=False,
                                   **form_choices(client_id)), 400
        flash("Action created.", "success")
        return redirect(url_for("actions.show", action_id=cur.lastrowid))

    defaults = {}
    if plan:
        moves = conn.execute(
            """SELECT value FROM plan_template_tags WHERE plan_template_id = ? AND kind = 'moves'
               ORDER BY value""", (plan["id"],)).fetchall()
        start = today()
        defaults = {
            "title": plan["title"], "discipline": plan["discipline"],
            "benefit_type": plan["benefit_type"], "lifecycle_stage": plan["lifecycle_stage"],
            "comparison": DEFAULT_COMPARISON[plan["benefit_type"]],
            "primary_metric": moves[0]["value"] if moves and plan["benefit_type"] != "enabler"
            else ("avoided_cost" if plan["benefit_type"] == "avoided_cost" else None),
            "setup_hours": plan["setup_hours"], "hurdle_eur": plan["default_hurdle_eur"],
            "post_period_days": plan["default_post_period_days"],
            "window_start": start.isoformat(),
            "window_end": measure.shift(start.isoformat(), plan["default_window_days"] - 1),
        }
    return render_template("action_form.html", client=client, plan=plan, action=defaults,
                           editing=False, **form_choices(client_id))


@bp.route("/actions/<int:action_id>")
@login_required
def show(action_id):
    action = get_action(action_id)
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (action["client_id"],)).fetchone()
    rate = client["hourly_rate_eur"]
    invested = roi.action_investment(action["setup_cost_eur"], action["setup_hours"],
                                     action["operating_cost_eur"], action["operating_hours"], rate)
    people = {u["id"]: u["full_name"] for u in conn.execute("SELECT id, full_name FROM users")}
    history = conn.execute(
        "SELECT * FROM action_history WHERE action_id = ? ORDER BY created_at, id", (action_id,)
    ).fetchall()
    measured = None
    guardrails = []
    # Nothing to show before the window starts: an empty future period compared
    # with the month before it would read as a large loss.
    started = action["window_start"] and action["window_start"] <= today().isoformat()
    if started and action["window_end"] and action["benefit_type"] == "contribution":
        measured = measure.action_measured_benefit(conn, action)
    if started and action["window_end"]:
        guardrails = measure.window_guardrail_breach(conn, action["client_id"],
                                                     action["window_start"], action["window_end"])
    benefit = action["measured_benefit_eur"]
    net = roi.action_net_benefit(benefit, invested) if benefit is not None else None
    plan = (conn.execute("SELECT * FROM plan_templates WHERE id = ?",
                         (action["plan_template_id"],)).fetchone()
            if action["plan_template_id"] else None)
    # The pilot's own groups: an adopted component keeps assigning customers
    # under the same action afterwards.
    period_end = (measure.measurement_period(action)[1] if action["window_end"]
                  else "9999-12-31")
    groups = conn.execute(
        """SELECT "group", COUNT(*) AS n FROM assignments
           WHERE action_id = ? AND substr(assigned_at, 1, 10) <= ? GROUP BY "group" """,
        (action_id, period_end)).fetchall()
    return render_template(
        "action.html", action=action, client=client, plan=plan, invested=invested, net=net,
        roi_value=roi.action_roi(benefit, invested) if benefit is not None else None,
        people=people, history=history, measured=measured, guardrails=guardrails,
        measurement_end=lifecycle.measurement_end(to_action(action)),
        groups={r["group"]: r["n"] for r in groups},
        allowed=sorted(lifecycle.ALLOWED[action["status"]] - {action["status"]}),
        choices=form_choices(action["client_id"]), today=today().isoformat())


@bp.route("/actions/<int:action_id>/edit", methods=["GET", "POST"])
@login_required
def edit(action_id):
    action = get_action(action_id, write=True)
    client = get_client(action["client_id"], write=True)
    conn = get_db()
    if request.method == "POST":
        try:
            values = read_form(request.form)
            changed = {k for k, v in values.items() if action[k] != v}
            lifecycle.check_edit(to_action(action), changed)
            if changed:
                benefit_type = values.get("benefit_type") or action["benefit_type"]
                comparison = values.get("comparison", action["comparison"])
                if comparison and comparison not in lifecycle.COMPARISONS_FOR[benefit_type]:
                    raise FormError(
                        f"a {benefit_type} action needs the comparison: "
                        + ", ".join(sorted(lifecycle.COMPARISONS_FOR[benefit_type])))
                current_scope = action["scope_channel"] if "scope_channel" in action.keys() else None
                check_scope(action["client_id"], values.get("scope_channel", current_scope),
                            comparison)
                sets =", ".join(f"{k} = ?" for k in changed)
                with transaction(conn):
                    conn.execute(f"UPDATE actions SET {sets} WHERE id = ?",
                                 (*(values[k] for k in changed), action_id))
        except (FormError, lifecycle.TransitionError, sqlite3.IntegrityError) as error:
            flash(f"Not saved: {error}", "error")
            return render_template("action_form.html", client=client, plan=None,
                                   action=request.form, editing=True, action_id=action_id,
                                   **form_choices(action["client_id"])), 400
        flash("Saved.", "success")
        return redirect(url_for("actions.show", action_id=action_id))
    return render_template("action_form.html", client=client, plan=None, action=action,
                           editing=True, action_id=action_id,
                           **form_choices(action["client_id"]))


def move(action_row, to_status: str, ctx: lifecycle.Context, note: str = "",
         updates: dict | None = None, outbound: str | None = None):
    """Check the transition, then write the change and its history row together."""
    updates = updates or {}
    candidate = to_action(action_row, **{k: v for k, v in updates.items()
                                         if k in lifecycle.Action.__dataclass_fields__})
    lifecycle.check_transition(candidate, to_status, actor(), ctx)
    conn = get_db()
    columns = {**updates, "status": to_status}
    sets = ", ".join(f"{k} = ?" for k in columns)
    with transaction(conn):
        # The WHERE on status makes a stale form fail instead of reviving a
        # cancelled action (the Week 3 bug).
        cur = conn.execute(f"UPDATE actions SET {sets} WHERE id = ? AND status = ?",
                           (*columns.values(), action_row["id"], action_row["status"]))
        if cur.rowcount != 1:
            raise lifecycle.TransitionError("the action changed in the meantime; reload it")
        record(conn, action_row["id"], action_row["status"], to_status, note)
        if outbound:
            conn.execute(
                "INSERT INTO outbound_events (event_type, client_id, entity_id) VALUES (?, ?, ?)",
                (outbound, action_row["client_id"], action_row["id"]))


def done(action_id, message):
    flash(message, "success")
    return redirect(url_for("actions.show", action_id=action_id))


def refused(action_id, error):
    flash(f"Refused: {error}", "error")
    return redirect(url_for("actions.show", action_id=action_id))


@bp.route("/actions/<int:action_id>/assign", methods=["POST"])
@login_required
def assign(action_id):
    action = get_action(action_id, write=True)
    leads = eligible_lead_ids(action["client_id"])
    people = {p["id"] for p in assigned_people(action["client_id"])}
    owner_id = request.form.get("owner_id", type=int)
    reviewer_id = request.form.get("reviewer_id", type=int)
    try:
        if owner_id not in people:
            raise lifecycle.TransitionError("the owner must work on this client")
        if reviewer_id is not None and reviewer_id not in leads:
            raise lifecycle.TransitionError(
                "the reviewer must be one of this client's assigned leads")
        move(action, "assigned", lifecycle.Context(today()),
             updates={"owner_id": owner_id, "reviewer_id": reviewer_id})
    except (lifecycle.TransitionError, sqlite3.IntegrityError) as error:
        return refused(action_id, error)
    return done(action_id, "Assigned.")


@bp.route("/actions/<int:action_id>/review", methods=["POST"])
@login_required
def send_to_review(action_id):
    action = get_action(action_id, write=True)
    ctx = lifecycle.Context(today(), eligible_reviewer_ids=eligible_lead_ids(action["client_id"]))
    try:
        move(action, "in_review", ctx, outbound="action.review_requested")
    except lifecycle.TransitionError as error:
        return refused(action_id, error)
    return done(action_id, "Sent to the named reviewer.")


@bp.route("/actions/<int:action_id>/approve", methods=["POST"])
@login_required
def approve(action_id):
    action = get_action(action_id, write=True)
    try:
        move(action, "approved", lifecycle.Context(today()),
             note=request.form.get("note", ""), outbound="action.approved")
    except lifecycle.TransitionError as error:
        return refused(action_id, error)
    return done(action_id, "Approved.")


@bp.route("/actions/<int:action_id>/reject", methods=["POST"])
@login_required
def reject(action_id):
    action = get_action(action_id, write=True)
    try:
        move(action, "rejected", lifecycle.Context(today()), note=request.form.get("note", ""),
             outbound="action.rejected")
    except lifecycle.TransitionError as error:
        return refused(action_id, error)
    return done(action_id, "Rejected.")


@bp.route("/actions/<int:action_id>/cancel", methods=["POST"])
@login_required
def cancel(action_id):
    action = get_action(action_id, write=True)
    try:
        move(action, "cancelled", lifecycle.Context(today()), note=request.form.get("note", ""))
    except lifecycle.TransitionError as error:
        return refused(action_id, error)
    return done(action_id, "Cancelled.")


@bp.route("/actions/<int:action_id>/close", methods=["POST"])
@login_required
def close(action_id):
    """Close with the evidence. A contribution result is the app's own figure;
    only an avoided cost is typed, by the reviewer, with its evidence note."""
    action = get_action(action_id, write=True)
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (action["client_id"],)).fetchone()
    form = request.form
    updates = {
        "decision": form.get("decision") or None,
        "decision_note": form.get("decision_note", "").strip() or None,
        "early_stop_reason": form.get("early_stop_reason") or None,
    }
    incomplete = False
    if action["benefit_type"] == "contribution":
        measured = measure.action_measured_benefit(conn, action)
        if measured is None or measured.benefit_eur is None:
            return refused(action_id, "the app could not measure a result for this action")
        updates["measured_benefit_eur"] = measured.benefit_eur
        updates["confidence"] = measured.confidence
        incomplete = measured.incomplete
    elif action["benefit_type"] == "avoided_cost":
        try:
            updates["measured_benefit_eur"] = float(form.get("measured_benefit_eur", ""))
        except ValueError:
            return refused(action_id, "an avoided cost needs the amount the invoices show")
        updates["confidence"] = "documented"
        updates["evidence_note"] = form.get("evidence_note", "").strip() or None
    invested = roi.action_investment(action["setup_cost_eur"], action["setup_hours"],
                                     action["operating_cost_eur"], action["operating_hours"],
                                     client["hourly_rate_eur"])
    benefit = updates.get("measured_benefit_eur")
    breached = any(gr.breached for gr in measure.window_guardrail_breach(
        conn, action["client_id"], action["window_start"], action["window_end"]))
    ctx = lifecycle.Context(
        today(), net_benefit_eur=None if benefit is None else benefit - invested,
        guardrail_breached=breached, result_incomplete=incomplete)
    try:
        move(action, "closed", ctx, note=updates["decision_note"] or "", updates=updates,
             outbound="action.closed")
    except lifecycle.TransitionError as error:
        return refused(action_id, error)

    if updates["decision"] == "adopt" and form.get("add_component") == "1":
        measurement = form.get("measurement")
        allowed = {"contribution": {"holdout_kept", "pilot_estimate"},
                   "avoided_cost": {"invoice"}, "enabler": {None}}[action["benefit_type"]]
        if measurement not in allowed:
            measurement = sorted(allowed, key=str)[0]
        with transaction(conn):
            conn.execute(
                """INSERT INTO components (client_id, origin_action_id, name, discipline,
                       lifecycle_stage, benefit_type, measurement, started_on, benefit_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (action["client_id"], action_id, action["title"], action["discipline"],
                 action["lifecycle_stage"], action["benefit_type"], measurement,
                 today().isoformat(), action["benefit_key"]))
        return done(action_id, "Closed and added to the growth system.")
    return done(action_id, "Closed.")
