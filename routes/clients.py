"""The client portfolio, each client's growth-system dashboard, and the plans."""

from flask import Blueprint, g, render_template, request

import lifecycle
import measure
import roi
from auth import assigned_client_ids, get_client, login_required, today
from db import get_db

bp = Blueprint("clients", __name__)


def latest_month(client_id: int) -> str | None:
    row = get_db().execute(
        "SELECT MAX(substr(ordered_at, 1, 7)) FROM orders WHERE client_id = ?", (client_id,)
    ).fetchone()
    return row[0]


def chosen_month(client_id: int) -> str | None:
    months = available_months(client_id)
    wanted = request.args.get("month")
    return wanted if wanted in months else (months[-1] if months else None)


def available_months(client_id: int) -> list[str]:
    return [r[0] for r in get_db().execute(
        """SELECT DISTINCT substr(ordered_at, 1, 7) FROM orders WHERE client_id = ?
           ORDER BY 1""", (client_id,))]


def refresh_review_due(client_id: int) -> None:
    """A pilot-estimate component is due for re-testing six months after it started."""
    conn = get_db()
    for c in conn.execute(
            "SELECT * FROM components WHERE client_id = ? AND status = 'running'", (client_id,)):
        if lifecycle.component_review_due(c["measurement"], c["started_on"], today()):
            conn.execute("UPDATE components SET status = 'review_due' WHERE id = ?", (c["id"],))
    conn.commit()


@bp.route("/")
@login_required
def portfolio():
    conn = get_db()
    if "admin" in g.roles:
        rows = conn.execute("SELECT * FROM clients WHERE is_active = 1 ORDER BY name").fetchall()
    else:
        ids = assigned_client_ids()
        rows = [c for c in conn.execute(
            "SELECT * FROM clients WHERE is_active = 1 ORDER BY name") if c["id"] in ids]
    cards = []
    for c in rows:
        month = latest_month(c["id"])
        system = measure.system_month(conn, c, month) if month else None
        cards.append({"client": c, "month": month, "system": system})
    return render_template("portfolio.html", cards=cards)


@bp.route("/clients/<int:client_id>")
@login_required
def dashboard(client_id):
    client = get_client(client_id)
    conn = get_db()
    refresh_review_due(client_id)
    month = chosen_month(client_id)
    if month is None:
        return render_template("dashboard.html", client=client, month=None)
    pnl = measure.growth_pnl(conn, client_id, month)
    current = measure.store_metrics(conn, client_id, month)
    baseline = measure.baseline_metrics(conn, client_id, month)
    system = measure.system_month(conn, client, month)
    history = [{"month": m, "system": measure.system_month(conn, client, m)}
               for m in available_months(client_id)]
    rate = client["hourly_rate_eur"]
    component_rows = measure.latest_component_months(conn, client_id, month)
    by_component = {r["component_id"]: r for r in component_rows}
    components = []
    for c in conn.execute("SELECT * FROM components WHERE client_id = ? ORDER BY started_on",
                          (client_id,)):
        row = by_component.get(c["id"])
        cost = (roi.component_month_cost(row["operating_cost_eur"], row["operating_hours"], rate)
                if row else None)
        benefit = row["measured_benefit_eur"] if row else None
        components.append({"c": c, "row": row, "cost": cost, "benefit": benefit,
                           "roi": roi.continuation_roi(benefit, cost) if row else None})
    pilots = conn.execute(
        """SELECT * FROM actions WHERE client_id = ? AND status IN
           ('submitted', 'assigned', 'in_review', 'approved') ORDER BY created_at DESC""",
        (client_id,),
    ).fetchall()
    return render_template(
        "dashboard.html", client=client, month=month, months=available_months(client_id),
        pnl=pnl, system=system, history=history,
        payback=measure.setup_payback_for(conn, client, month),
        guardrails=measure.guardrails(current, baseline),
        grow=measure.where_to_grow(conn, client, month),
        components=components, pilots=pilots)


@bp.route("/clients/<int:client_id>/details")
@login_required
def details(client_id):
    client = get_client(client_id)
    conn = get_db()
    month = chosen_month(client_id)
    if month is None:
        return render_template("details.html", client=client, month=None)
    current = measure.store_metrics(conn, client_id, month)
    baseline = measure.baseline_metrics(conn, client_id, month)
    return render_template(
        "details.html", client=client, month=month, months=available_months(client_id),
        current=current, baseline=baseline,
        channels=measure.channel_metrics(conn, client_id, month),
        quality=measure.quality_metrics(conn, client_id, month),
        stages=measure.stage_summary(conn, client, month))


@bp.route("/clients/<int:client_id>/plans")
@login_required
def plans(client_id):
    client = get_client(client_id)
    conn = get_db()
    rows = conn.execute(
        """
        SELECT p.*,
          (SELECT GROUP_CONCAT(value, ', ') FROM plan_template_tags t
            WHERE t.plan_template_id = p.id AND t.kind = 'moves') AS moves,
          (NOT EXISTS (SELECT 1 FROM plan_template_tags b WHERE b.plan_template_id = p.id
                       AND b.kind = 'business_model')
           OR EXISTS (SELECT 1 FROM plan_template_tags b WHERE b.plan_template_id = p.id
                      AND b.kind = 'business_model' AND b.value = :model))
          AND (NOT EXISTS (SELECT 1 FROM plan_template_tags f WHERE f.plan_template_id = p.id
                           AND f.kind = 'purchase_frequency')
               OR EXISTS (SELECT 1 FROM plan_template_tags f WHERE f.plan_template_id = p.id
                          AND f.kind = 'purchase_frequency' AND f.value = :frequency)) AS suits
        FROM plan_templates p
        ORDER BY suits DESC, featured DESC, data_fit = 'no', id
        """,
        {"model": client["business_model"], "frequency": client["purchase_frequency"]},
    ).fetchall()
    return render_template("plans.html", client=client, plans=rows)
