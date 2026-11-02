"""Measured figures from the shop data (spec v2 §4).

Contribution of an order, the Growth P&L, an action's measured benefit, the
store's driver, efficiency and guardrail metrics, "where to grow", and a
client's growth-system month. Free of Flask: it takes a sqlite3 connection and
plain values, so it can be tested directly.

Two rules run through everything here:

* A missing cost is never zero. A figure that depends on one is *incomplete*.
* The store's own contribution is context, never the agency's result. Only
  measured, incremental results count as an action's or a component's benefit.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta

import roi

# Guardrail tolerances (spec v2 §4) — illustrative constants, stated so that
# random variation in the data does not count as a breach.
MARGIN_TOLERANCE_POINTS = 2.0
REFUND_TOLERANCE_POINTS = 1.0
# "Where to grow": the other metrics are weak when worse than their own
# three-month average by more than this share.
RELATIVE_TOLERANCE = 0.05
BASELINE_MONTHS = 3
REPEAT_WINDOW_DAYS = 90


# --- dates -------------------------------------------------------------------

def month_range(month: str) -> tuple[str, str]:
    """First and last day of a 'YYYY-MM' month, as ISO dates."""
    year, mon = (int(p) for p in month.split("-"))
    first = date(year, mon, 1)
    nxt = date(year + (mon == 12), mon % 12 + 1, 1)
    return first.isoformat(), (nxt - timedelta(days=1)).isoformat()


def previous_months(month: str, n: int) -> list[str]:
    year, mon = (int(p) for p in month.split("-"))
    out = []
    for _ in range(n):
        mon -= 1
        if mon == 0:
            year, mon = year - 1, 12
        out.append(f"{year:04d}-{mon:02d}")
    return out


def days_between(start: str, end: str) -> int:
    """Days from start to end inclusive."""
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


# --- one order ---------------------------------------------------------------

def order_contribution(net_revenue: float, product_cost: float | None,
                       shipping_cost: float | None, payment_fee: float | None,
                       refunded: float = 0.0, restocked: float = 0.0) -> float | None:
    """Net revenue minus costs and refunds, plus product cost recovered.

    Discounts are already inside net revenue and are never subtracted again.
    None when any cost is missing: incomplete, not zero.
    """
    if product_cost is None or shipping_cost is None or payment_fee is None:
        return None
    return net_revenue - product_cost - shipping_cost - payment_fee - refunded + restocked


@dataclass
class Contribution:
    total: float = 0.0
    orders: int = 0
    incomplete: bool = False
    by_customer: dict[str, float] = field(default_factory=dict)


def contribution_between(conn: sqlite3.Connection, client_id: int, start: str, end: str,
                         refunds_until: str | None = None) -> Contribution:
    """Contribution of the orders placed between start and end (inclusive).

    Refunds count when recorded by refunds_until (default: end) — an action's
    result never changes because of a refund recorded after its period.
    """
    refunds_until = refunds_until or end
    rows = conn.execute(
        """
        SELECT o.customer_ref, o.net_revenue_eur, o.product_cost_eur,
               o.shipping_cost_eur, o.payment_fee_eur,
               COALESCE(SUM(r.amount_eur), 0) AS refunded,
               COALESCE(SUM(r.restocked_cost_eur), 0) AS restocked
        FROM orders o
        LEFT JOIN refunds r
               ON r.order_id = o.id AND substr(r.refunded_at, 1, 10) <= :until
        WHERE o.client_id = :client AND substr(o.ordered_at, 1, 10) BETWEEN :start AND :end
        GROUP BY o.id
        """,
        {"client": client_id, "start": start, "end": end, "until": refunds_until},
    ).fetchall()
    result = Contribution()
    for r in rows:
        value = order_contribution(r["net_revenue_eur"], r["product_cost_eur"],
                                   r["shipping_cost_eur"], r["payment_fee_eur"],
                                   r["refunded"], r["restocked"])
        result.orders += 1
        if value is None:
            result.incomplete = True
            continue
        result.total += value
        result.by_customer[r["customer_ref"]] = (
            result.by_customer.get(r["customer_ref"], 0.0) + value
        )
    return result


# --- an action's measured benefit ---------------------------------------------

@dataclass(frozen=True)
class MeasuredBenefit:
    benefit_eur: float | None
    confidence: str | None
    incomplete: bool
    detail: str


def measurement_period(action: sqlite3.Row) -> tuple[str, str]:
    """Window start to window end plus the post-period."""
    end = shift(action["window_end"], action["post_period_days"] or 0)
    return action["window_start"], end


def holdout_benefit(conn: sqlite3.Connection, client_id: int, action_id: int,
                    start: str, end: str, assigned_from: str | None = None) -> MeasuredBenefit:
    """(contribution per assigned test customer − per assigned control customer)
    × customers assigned to test. Every assigned customer counts, buyers or not.

    assigned_from limits the groups to customers assigned from that date — a
    running component's month counts that month's entrants only.
    """
    groups = conn.execute(
        """SELECT customer_ref, "group" FROM assignments
           WHERE action_id = ? AND substr(assigned_at, 1, 10) BETWEEN ? AND ?""",
        (action_id, assigned_from or "0000-00-00", end),
    ).fetchall()
    test = {g["customer_ref"] for g in groups if g["group"] == "test"}
    control = {g["customer_ref"] for g in groups if g["group"] == "control"}
    if not test or not control:
        return MeasuredBenefit(None, "holdout", False, "no test or control customers assigned")
    contrib = contribution_between(conn, client_id, start, end)
    test_total = sum(v for k, v in contrib.by_customer.items() if k in test)
    control_total = sum(v for k, v in contrib.by_customer.items() if k in control)
    per_test = test_total / len(test)
    per_control = control_total / len(control)
    benefit = (per_test - per_control) * len(test)
    detail = (f"{len(test)} test and {len(control)} control customers; "
              f"€{per_test:.2f} vs €{per_control:.2f} contribution per customer")
    return MeasuredBenefit(benefit, "holdout", contrib.incomplete, detail)


def before_after_benefit(conn: sqlite3.Connection, client_id: int,
                         start: str, end: str) -> MeasuredBenefit:
    """Contribution in the period minus the equal-length period just before it."""
    length = days_between(start, end)
    before_end = shift(start, -1)
    before_start = shift(start, -length)
    after = contribution_between(conn, client_id, start, end)
    before = contribution_between(conn, client_id, before_start, before_end)
    detail = (f"€{after.total:,.0f} in {start}–{end} against €{before.total:,.0f} "
              f"in {before_start}–{before_end}")
    return MeasuredBenefit(after.total - before.total, "before_after",
                           after.incomplete or before.incomplete, detail)


def action_measured_benefit(conn: sqlite3.Connection, action: sqlite3.Row) -> MeasuredBenefit | None:
    """The app's own figure for a contribution action; None for other types."""
    if action["benefit_type"] != "contribution" or not action["window_end"]:
        return None
    start, end = measurement_period(action)
    if action["comparison"] == "holdout":
        return holdout_benefit(conn, action["client_id"], action["id"], start, end)
    if action["comparison"] == "before_after":
        return before_after_benefit(conn, action["client_id"], start, end)
    return None


# --- store metrics -------------------------------------------------------------

def sessions_between(conn, client_id, start, end) -> int:
    return conn.execute(
        "SELECT COALESCE(SUM(sessions), 0) FROM sessions WHERE client_id = ? AND date BETWEEN ? AND ?",
        (client_id, start, end),
    ).fetchone()[0]


def spend_by_channel(conn, client_id, start, end) -> dict[str, float]:
    rows = conn.execute(
        """SELECT channel, SUM(spend_eur) AS spend FROM ad_spend
           WHERE client_id = ? AND date BETWEEN ? AND ? GROUP BY channel""",
        (client_id, start, end),
    ).fetchall()
    return {r["channel"]: r["spend"] for r in rows}


@dataclass
class Line:
    value: float | None
    incomplete: bool = False


def growth_pnl(conn: sqlite3.Connection, client_id: int, month: str) -> dict:
    """The store's health for one month — the context, not the agency's result."""
    start, end = month_range(month)
    return {"month": month, **period_pnl(conn, client_id, start, end)}


def period_pnl(conn: sqlite3.Connection, client_id: int, start: str, end: str) -> dict:
    """Growth P&L lines for any period. Refunds are those recorded in the period,
    so a recent period is not flattered by refunds that have not arrived yet."""
    o = conn.execute(
        """
        SELECT COUNT(*) AS orders,
               COALESCE(SUM(net_revenue_eur), 0) AS revenue,
               COALESCE(SUM(discount_eur), 0) AS discounts,
               COALESCE(SUM(product_cost_eur), 0) AS product,
               COALESCE(SUM(shipping_cost_eur), 0) AS shipping,
               COALESCE(SUM(payment_fee_eur), 0) AS fees,
               -- a plain SUM() skips NULLs: count the missing costs explicitly
               SUM(product_cost_eur IS NULL) AS missing_product,
               SUM(shipping_cost_eur IS NULL OR payment_fee_eur IS NULL) AS missing_fees
        FROM orders WHERE client_id = ? AND substr(ordered_at, 1, 10) BETWEEN ? AND ?
        """,
        (client_id, start, end),
    ).fetchone()
    r = conn.execute(
        """
        SELECT COALESCE(SUM(r.amount_eur), 0) AS refunds,
               COALESCE(SUM(r.restocked_cost_eur), 0) AS restocked
        FROM refunds r JOIN orders o ON o.id = r.order_id
        WHERE o.client_id = ? AND substr(r.refunded_at, 1, 10) BETWEEN ? AND ?
        """,
        (client_id, start, end),
    ).fetchone()
    sessions = sessions_between(conn, client_id, start, end)
    spend = sum(spend_by_channel(conn, client_id, start, end).values())
    orders = o["orders"]
    revenue = o["revenue"]
    missing_product = bool(o["missing_product"])
    missing_fees = bool(o["missing_fees"])
    any_missing = missing_product or missing_fees

    before_marketing = (revenue - r["refunds"] - (o["product"] - r["restocked"])
                        - o["shipping"] - o["fees"])
    base = revenue - r["refunds"]
    refunded_orders = conn.execute(
        """SELECT COUNT(DISTINCT r.order_id) FROM refunds r JOIN orders o ON o.id = r.order_id
           WHERE o.client_id = ? AND substr(r.refunded_at, 1, 10) BETWEEN ? AND ?""",
        (client_id, start, end),
    ).fetchone()[0]
    return {
        "sessions": Line(sessions),
        "orders": Line(orders),
        "conversion": Line(orders / sessions if sessions else None),
        "average_order_value": Line(revenue / orders if orders else None),
        "discounts": Line(o["discounts"]),
        "net_revenue": Line(revenue),
        "refunds": Line(r["refunds"]),
        "product_cost": Line(o["product"] - r["restocked"], missing_product),
        "shipping_and_fees": Line(o["shipping"] + o["fees"], missing_fees),
        "contribution_before_marketing": Line(before_marketing, any_missing),
        "ad_spend": Line(spend),
        "contribution_after_marketing": Line(before_marketing - spend, any_missing),
        "margin_pct": Line(before_marketing / base * 100 if base else None, any_missing),
        # Orders refunded in the period ÷ orders placed in the period.
        "refund_rate": Line(refunded_orders / orders * 100 if orders else None),
    }


def store_metrics(conn: sqlite3.Connection, client_id: int, month: str) -> dict[str, float | None]:
    """Driver, efficiency and guardrail metrics for one month, in the shared vocabulary."""
    start, end = month_range(month)
    pnl = growth_pnl(conn, client_id, month)
    orders = pnl["orders"].value
    new_customers = conn.execute(
        """SELECT COUNT(*) FROM orders WHERE client_id = ? AND is_new_customer = 1
           AND substr(ordered_at, 1, 10) BETWEEN ? AND ?""",
        (client_id, start, end),
    ).fetchone()[0]
    window_start = shift(end, -(REPEAT_WINDOW_DAYS - 1))
    counts = conn.execute(
        """SELECT customer_ref, COUNT(*) AS n FROM orders WHERE client_id = ?
           AND substr(ordered_at, 1, 10) BETWEEN ? AND ? GROUP BY customer_ref""",
        (client_id, window_start, end),
    ).fetchall()
    buyers = len(counts)
    repeaters = sum(1 for c in counts if c["n"] >= 2)
    spend = pnl["ad_spend"].value
    return {
        "revenue": pnl["net_revenue"].value,
        "orders": orders,
        "sessions": pnl["sessions"].value,
        "conversion": pnl["conversion"].value,
        "average_order_value": pnl["average_order_value"].value,
        "new_customers": new_customers,
        "repeat_rate": repeaters / buyers if buyers else None,
        "cac": spend / new_customers if new_customers else None,
        "cpa": spend / orders if orders else None,
        "refund_rate": pnl["refund_rate"].value,
        "margin_pct": None if pnl["margin_pct"].incomplete else pnl["margin_pct"].value,
    }


def channel_metrics(conn: sqlite3.Connection, client_id: int, month: str) -> list[dict]:
    """CPA and ROAS by paid channel. ROAS is a diagnostic, never a result."""
    start, end = month_range(month)
    spend = spend_by_channel(conn, client_id, start, end)
    out = []
    for channel, amount in sorted(spend.items()):
        row = conn.execute(
            """SELECT COUNT(*) AS orders, COALESCE(SUM(net_revenue_eur), 0) AS revenue,
                      SUM(is_new_customer) AS new_customers
               FROM orders WHERE client_id = ? AND channel = ?
               AND substr(ordered_at, 1, 10) BETWEEN ? AND ?""",
            (client_id, channel, start, end),
        ).fetchone()
        out.append({
            "channel": channel,
            "spend": amount,
            "orders": row["orders"],
            "cpa": amount / row["orders"] if row["orders"] else None,
            "cac": amount / row["new_customers"] if row["new_customers"] else None,
            "roas": row["revenue"] / amount if amount else None,
        })
    return out


# --- guardrails and where to grow ------------------------------------------------

HIGHER_IS_BETTER = {
    "orders": True, "sessions": True, "conversion": True, "average_order_value": True,
    "new_customers": True, "repeat_rate": True, "cac": False, "cpa": False,
    "refund_rate": False, "margin_pct": True,
}
POINT_TOLERANCE = {"margin_pct": MARGIN_TOLERANCE_POINTS,
                   "refund_rate": REFUND_TOLERANCE_POINTS}


def is_worse(metric: str, current: float | None, baseline: float | None) -> bool:
    """Worse than baseline by more than the metric's tolerance."""
    if current is None or baseline is None:
        return False
    if metric in POINT_TOLERANCE:
        gap = POINT_TOLERANCE[metric]
        return current < baseline - gap if HIGHER_IS_BETTER[metric] else current > baseline + gap
    if baseline == 0:
        return False
    change = (current - baseline) / abs(baseline)
    return change < -RELATIVE_TOLERANCE if HIGHER_IS_BETTER[metric] else change > RELATIVE_TOLERANCE


def baseline_metrics(conn, client_id: int, month: str) -> dict[str, float | None]:
    """Average of each metric over the previous three months."""
    months = [store_metrics(conn, client_id, m) for m in previous_months(month, BASELINE_MONTHS)]
    out = {}
    for metric in HIGHER_IS_BETTER:
        values = [m[metric] for m in months if m[metric] is not None]
        out[metric] = sum(values) / len(values) if len(values) == BASELINE_MONTHS else None
    return out


@dataclass(frozen=True)
class Guardrail:
    metric: str
    current: float | None
    baseline: float | None
    breached: bool


def guardrails(current: dict, baseline: dict) -> list[Guardrail]:
    return [Guardrail(m, current[m], baseline[m], is_worse(m, current[m], baseline[m]))
            for m in ("margin_pct", "refund_rate")]


def window_guardrail_breach(conn, client_id: int, start: str, end: str) -> list[Guardrail]:
    """An action's guardrails over its window against the three months before it."""
    def figures(s, e):
        pnl = period_pnl(conn, client_id, s, e)
        margin = pnl["margin_pct"]
        return {"margin_pct": None if margin.incomplete else margin.value,
                "refund_rate": pnl["refund_rate"].value}

    current = figures(start, end)
    baseline = figures(shift(start, -91), shift(start, -1))
    return guardrails(current, baseline)


def where_to_grow(conn: sqlite3.Connection, client: sqlite3.Row, month: str) -> list[dict]:
    """Each weak metric with the plans that target it — never 'the app recommends'."""
    current = store_metrics(conn, client["id"], month)
    baseline = baseline_metrics(conn, client["id"], month)
    weak = [m for m in HIGHER_IS_BETTER if is_worse(m, current[m], baseline[m])]
    out = []
    for metric in weak:
        plans = conn.execute(
            """
            SELECT p.id, p.title, p.discipline, p.data_fit, p.featured
            FROM plan_templates p
            JOIN plan_template_tags t
              ON t.plan_template_id = p.id AND t.kind = 'moves' AND t.value = :metric
            WHERE p.data_fit <> 'no'
              AND (NOT EXISTS (SELECT 1 FROM plan_template_tags b
                               WHERE b.plan_template_id = p.id AND b.kind = 'business_model')
                   OR EXISTS (SELECT 1 FROM plan_template_tags b
                              WHERE b.plan_template_id = p.id AND b.kind = 'business_model'
                                AND b.value = :model))
              AND (NOT EXISTS (SELECT 1 FROM plan_template_tags f
                               WHERE f.plan_template_id = p.id AND f.kind = 'purchase_frequency')
                   OR EXISTS (SELECT 1 FROM plan_template_tags f
                              WHERE f.plan_template_id = p.id AND f.kind = 'purchase_frequency'
                                AND f.value = :frequency))
            ORDER BY p.featured DESC, p.data_fit = 'yes' DESC, p.id
            """,
            {"metric": metric, "model": client["business_model"],
             "frequency": client["purchase_frequency"]},
        ).fetchall()
        out.append({"metric": metric, "current": current[metric],
                    "baseline": baseline[metric], "plans": [dict(p) for p in plans]})
    return out


# --- the growth system ----------------------------------------------------------

def latest_component_months(conn: sqlite3.Connection, client_id: int, month: str) -> list[sqlite3.Row]:
    """This month's rows for a client's components, corrections applied."""
    return conn.execute(
        """
        SELECT cm.*, c.name, c.benefit_type, c.measurement, c.status AS component_status
        FROM component_months cm JOIN components c ON c.id = cm.component_id
        WHERE cm.client_id = ? AND cm.month = ?
          AND NOT EXISTS (SELECT 1 FROM component_months newer WHERE newer.supersedes_id = cm.id)
        ORDER BY c.name
        """,
        (client_id, month),
    ).fetchall()


def system_month(conn: sqlite3.Connection, client: sqlite3.Row, month: str) -> roi.SystemResult:
    rate = client["hourly_rate_eur"]
    rows = latest_component_months(conn, client["id"], month)
    return roi.system_result(
        roi.ComponentMonth(r["benefit_key"], r["measured_benefit_eur"],
                           roi.component_month_cost(r["operating_cost_eur"],
                                                    r["operating_hours"], rate))
        for r in rows
    )


def setup_payback_for(conn: sqlite3.Connection, client: sqlite3.Row, month: str) -> dict:
    """Cumulative net benefit of running components against their setup cost."""
    rate = client["hourly_rate_eur"]
    setup = conn.execute(
        """SELECT COALESCE(SUM(a.setup_cost_eur + a.setup_hours * ?), 0)
           FROM components c JOIN actions a ON a.id = c.origin_action_id
           WHERE c.client_id = ? AND c.status <> 'retired'""",
        (rate, client["id"]),
    ).fetchone()[0]
    months = [r[0] for r in conn.execute(
        "SELECT DISTINCT month FROM component_months WHERE client_id = ? AND month <= ? ORDER BY month",
        (client["id"], month),
    )]
    cumulative = sum(system_month(conn, client, m).net_eur for m in months)
    return {"setup_eur": setup, "cumulative_net_eur": cumulative,
            "share": roi.setup_payback(cumulative, setup)}


def component_benefit_for_month(conn: sqlite3.Connection, component: sqlite3.Row,
                                month: str) -> tuple[float | None, str | None]:
    """The app's benefit figure for holdout_kept and pilot_estimate components."""
    if component["measurement"] == "holdout_kept":
        start, end = month_range(month)
        result = holdout_benefit(conn, component["client_id"], component["origin_action_id"],
                                 start, end, assigned_from=start)
        if result.incomplete:
            return None, "holdout"
        return result.benefit_eur, "holdout"
    if component["measurement"] == "pilot_estimate":
        origin = conn.execute("SELECT * FROM actions WHERE id = ?",
                              (component["origin_action_id"],)).fetchone()
        if origin is None or origin["measured_benefit_eur"] is None:
            return None, "pilot_estimate"
        start, end = measurement_period(origin)
        per_day = origin["measured_benefit_eur"] / days_between(start, end)
        m_start, m_end = month_range(month)
        return per_day * days_between(m_start, m_end), "pilot_estimate"
    return None, None


def quality_metrics(conn: sqlite3.Connection, client_id: int, month: str) -> dict:
    """Watches the system itself: intake, missing costs, failed runs, alerts, reports."""
    start, end = month_range(month)
    batches = conn.execute(
        """SELECT status, COUNT(*) AS n FROM automation_events
           WHERE client_id = ? AND event_type = 'shop_data'
           AND substr(received_at, 1, 10) BETWEEN ? AND ? GROUP BY status""",
        (client_id, start, end),
    ).fetchall()
    counts = {b["status"]: b["n"] for b in batches}
    received = sum(counts.values())
    alerts = conn.execute(
        """SELECT COUNT(*) FROM automation_events WHERE client_id = ? AND event_type = 'alerts'
           AND status = 'accepted' AND substr(received_at, 1, 10) BETWEEN ? AND ?""",
        (client_id, start, end),
    ).fetchone()[0]
    missing = conn.execute(
        """SELECT COUNT(*) FROM orders WHERE client_id = ?
           AND substr(ordered_at, 1, 10) BETWEEN ? AND ?
           AND (product_cost_eur IS NULL OR shipping_cost_eur IS NULL OR payment_fee_eur IS NULL)""",
        (client_id, start, end),
    ).fetchone()[0]
    runs = conn.execute(
        """SELECT COALESCE(SUM(runs), 0), COALESCE(SUM(failed_runs), 0),
                  COALESCE(SUM(hours_freed), 0)
           FROM component_months cm WHERE client_id = ? AND month = ?
           AND NOT EXISTS (SELECT 1 FROM component_months n WHERE n.supersedes_id = cm.id)""",
        (client_id, month),
    ).fetchone()
    return {
        "batches_received": received,
        "batches_rejected": counts.get("rejected", 0),
        "batches_duplicate": counts.get("duplicate", 0),
        "intake_quality": counts.get("accepted", 0) / received if received else None,
        "orders_missing_cost": missing,
        "runs": runs[0],
        "failed_runs": runs[1],
        "hours_freed": runs[2],
        "open_alerts": alerts,
        **report_quality(conn, client_id),
    }


def report_quality(conn: sqlite3.Connection, client_id: int | None = None) -> dict:
    """Correction rate, rejection rate and cost per draft, from stored reports."""
    where, params = ("WHERE client_id = ?", (client_id,)) if client_id else ("", ())
    row = conn.execute(
        f"""SELECT COUNT(*) AS drafts,
                   SUM(status <> 'draft') AS reviewed,
                   SUM(status = 'sent' AND was_corrected = 1) AS corrected,
                   SUM(status = 'rejected') AS rejected,
                   COALESCE(SUM(generation_cost_eur), 0) AS cost
            FROM client_reports {where}""",
        params,
    ).fetchone()
    reviewed = row["reviewed"] or 0
    return {
        "reports_drafted": row["drafts"],
        "correction_rate": (row["corrected"] or 0) / reviewed if reviewed else None,
        "rejection_rate": (row["rejected"] or 0) / reviewed if reviewed else None,
        "cost_per_draft": row["cost"] / row["drafts"] if row["drafts"] else None,
    }


def stage_summary(conn: sqlite3.Connection, client: sqlite3.Row, month: str) -> list[dict]:
    """Investment and benefit per lifecycle stage, so strong and weak stages show."""
    rate = client["hourly_rate_eur"]
    rows = latest_component_months(conn, client["id"], month)
    stages: dict[str, dict] = {}
    comp_stage = {c["id"]: c["lifecycle_stage"] for c in conn.execute(
        "SELECT id, lifecycle_stage FROM components WHERE client_id = ?", (client["id"],))}
    for r in rows:
        stage = comp_stage[r["component_id"]]
        s = stages.setdefault(stage, {"stage": stage, "cost": 0.0, "benefit": 0.0})
        s["cost"] += roi.component_month_cost(r["operating_cost_eur"], r["operating_hours"], rate)
        s["benefit"] += r["measured_benefit_eur"] or 0.0
    return sorted(stages.values(), key=lambda s: s["stage"] == "operations")
