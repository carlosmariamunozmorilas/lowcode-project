"""Money and measurement: spec v2 §11 tests 1–4, 6–8, 10, 26, 28–30, 41, 42."""

import sqlite3

import pytest

import measure
import roi
from conftest import (CONSULTANT, LEAD_A, LUNA, add_action, add_order, add_refund,
                      assign_customers)


def test_01_order_contribution_never_subtracts_the_discount_again():
    # Net revenue is already after the €20 discount; only costs and refunds come off.
    value = measure.order_contribution(80.0, 30.0, 5.0, 2.0, refunded=10.0, restocked=4.0)
    assert value == pytest.approx(80 - 30 - 5 - 2 - 10 + 4)


def test_01b_missing_cost_is_incomplete_not_zero():
    assert measure.order_contribution(80.0, None, 5.0, 2.0) is None


def test_02_holdout_counts_every_assigned_customer_including_non_buyers(conn):
    action = add_action(conn, comparison="holdout", window_start="2026-06-01",
                        window_end="2026-06-10", post_period_days=0)
    other = add_action(conn, comparison="holdout", window_start="2026-06-01",
                       window_end="2026-06-10", post_period_days=0)
    # Four test customers, one buys; four control customers, none buys.
    assign_customers(conn, action, ["T1", "T2", "T3", "T4"], ["C1", "C2", "C3", "C4"])
    assign_customers(conn, other, ["T1"], ["C9"])   # T1 is in two actions at once
    add_order(conn, "2026-06-05", "T1", revenue=100, product=40, shipping=5, fee=2)  # 53
    result = measure.holdout_benefit(conn, LUNA, action, "2026-06-01", "2026-06-10")
    # (53/4 − 0/4) × 4 test customers = 53, not (53/1 − 0) × 4 = 212.
    assert result.benefit_eur == pytest.approx(53.0)
    assert result.confidence == "holdout"
    second = measure.holdout_benefit(conn, LUNA, other, "2026-06-01", "2026-06-10")
    assert second.benefit_eur == pytest.approx(53.0)


def test_03_before_after_compares_equal_length_periods(conn):
    add_order(conn, "2026-06-03", "A", revenue=100)   # before: 1 order
    add_order(conn, "2026-06-12", "B", revenue=100)   # after: 2 orders
    add_order(conn, "2026-06-18", "C", revenue=100)
    add_order(conn, "2026-06-21", "D", revenue=100)   # outside both
    result = measure.before_after_benefit(conn, LUNA, "2026-06-11", "2026-06-20")
    assert result.benefit_eur == pytest.approx(53.0)
    assert result.confidence == "before_after"
    assert "2026-06-01" in result.detail and "2026-06-10" in result.detail


def test_04_action_net_benefit_includes_setup_operating_and_hours():
    invested = roi.action_investment(300, 16, 120, 6, 35.0)
    assert invested == pytest.approx(300 + 16 * 35 + 120 + 6 * 35)
    assert roi.action_net_benefit(2000, invested) == pytest.approx(2000 - 1190)
    assert roi.action_roi(2000, invested) == pytest.approx(810 / 1190)
    assert roi.action_roi(100, 0) is None


def test_06_continuation_roi_excludes_setup():
    month_cost = roi.component_month_cost(120, 6, 35.0)
    assert month_cost == pytest.approx(330)
    assert roi.continuation_roi(660, month_cost) == pytest.approx(1.0)


def test_07_each_benefit_key_counted_once():
    result = roi.system_result([
        roi.ComponentMonth("luna:cart", 1000, 200),
        roi.ComponentMonth("luna:cart", 1000, 100),   # same outcome: cost only
        roi.ComponentMonth("luna:report", 500, 100),
    ])
    assert result.benefit_eur == 1500
    assert result.cost_eur == 400
    assert result.roi == pytest.approx(1100 / 400)


def test_07b_schema_refuses_a_second_benefit_for_the_same_key_and_month(conn):
    for name in ("Flow A", "Flow B"):
        conn.execute(
            """INSERT INTO components (client_id, name, discipline, lifecycle_stage, benefit_type,
                   measurement, started_on, benefit_key)
               VALUES (?, ?, 'automations', 'conversion', 'contribution', 'holdout_kept',
                       '2026-07-01', 'luna:cart')""", (LUNA, name))
    conn.execute("""INSERT INTO component_months (component_id, client_id, month,
                        measured_benefit_eur, benefit_key, recorded_by)
                    VALUES (1, ?, '2026-08', 900, 'luna:cart', ?)""", (LUNA, CONSULTANT))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("""INSERT INTO component_months (component_id, client_id, month,
                            measured_benefit_eur, benefit_key, recorded_by)
                        VALUES (2, ?, '2026-08', 900, 'luna:cart', ?)""", (LUNA, CONSULTANT))
    # Cost only for the second component is allowed.
    conn.execute("""INSERT INTO component_months (component_id, client_id, month,
                        operating_cost_eur, benefit_key, recorded_by)
                    VALUES (2, ?, '2026-08', 50, 'luna:cart', ?)""", (LUNA, CONSULTANT))


def test_08_an_enabler_never_shows_a_benefit_or_roi():
    assert roi.continuation_roi(None, 300) is None
    result = roi.system_result([roi.ComponentMonth(None, None, 300)])
    assert result.benefit_eur == 0 and result.cost_eur == 300


def test_10_hours_freed_never_enter_a_benefit(conn):
    conn.execute(
        """INSERT INTO components (id, client_id, name, discipline, lifecycle_stage, benefit_type,
               measurement, started_on, benefit_key)
           VALUES (1, ?, 'Agent', 'agentic_ai', 'operations', 'avoided_cost', 'invoice',
                   '2026-07-01', 'k')""", (LUNA,))
    conn.execute("""INSERT INTO component_months (component_id, client_id, month,
                        operating_cost_eur, measured_benefit_eur, benefit_key, hours_freed,
                        recorded_by) VALUES (1, ?, '2026-08', 100, 200, 'k', 40, ?)""",
                 (LUNA, LEAD_A))
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (LUNA,)).fetchone()
    system = measure.system_month(conn, client, "2026-08")
    assert system.benefit_eur == 200        # 40 freed hours × €35 would have been €1,400
    assert measure.quality_metrics(conn, LUNA, "2026-08")["hours_freed"] == 40


def _months_of_orders(conn, months: dict[str, tuple[int, float]]):
    """Orders per month: (count, product cost per €100 order)."""
    for month, (count, product) in months.items():
        for i in range(count):
            add_order(conn, f"{month}-{(i % 27) + 1:02d}", f"{month}-{i}", product=product)


def test_26_guardrail_breach_needs_more_than_the_tolerance(conn):
    _months_of_orders(conn, {"2026-07": (10, 40), "2026-08": (10, 40), "2026-09": (10, 40),
                             "2026-10": (10, 42)})
    current = measure.store_metrics(conn, LUNA, "2026-10")
    baseline = measure.baseline_metrics(conn, LUNA, "2026-10")
    margin = {g.metric: g for g in measure.guardrails(current, baseline)}["margin_pct"]
    assert margin.current == pytest.approx(51.0) and margin.baseline == pytest.approx(53.0)
    assert not margin.breached      # exactly 2 points lower: within tolerance
    conn.execute("UPDATE orders SET product_cost_eur = 43 WHERE ordered_at LIKE '2026-10%'")
    current = measure.store_metrics(conn, LUNA, "2026-10")
    margin = {g.metric: g for g in measure.guardrails(current, baseline)}["margin_pct"]
    assert margin.breached          # 3 points lower


def test_28_growth_pnl_adds_up_and_its_identity_holds(conn):
    o1 = add_order(conn, "2026-08-02", "A", revenue=90, discount=10, product=40, shipping=5, fee=2)
    add_order(conn, "2026-08-03", "B", revenue=110, product=50, shipping=6, fee=3)
    add_refund(conn, o1, "2026-08-10", 90, restocked=20)
    conn.execute("INSERT INTO sessions (client_id, date, channel, sessions) VALUES (?, '2026-08-01', 'meta', 100)", (LUNA,))
    conn.execute("INSERT INTO ad_spend (client_id, date, channel, spend_eur) VALUES (?, '2026-08-01', 'meta', 30)", (LUNA,))
    p = measure.growth_pnl(conn, LUNA, "2026-08")
    assert p["net_revenue"].value == 200
    assert p["discounts"].value == 10           # shown, never subtracted again
    before = 200 - 90 - (90 - 20) - (11 + 5)
    assert p["contribution_before_marketing"].value == pytest.approx(before)
    assert p["contribution_after_marketing"].value == pytest.approx(before - 30)
    identity = p["sessions"].value * p["conversion"].value * p["average_order_value"].value
    assert identity == pytest.approx(p["net_revenue"].value)


def test_29_missing_cost_makes_dependent_lines_incomplete(conn):
    add_order(conn, "2026-08-02", "A", revenue=100, product=40)
    add_order(conn, "2026-08-03", "B", revenue=100, product=None)
    p = measure.growth_pnl(conn, LUNA, "2026-08")
    assert p["product_cost"].incomplete
    assert p["contribution_before_marketing"].incomplete
    assert not p["net_revenue"].incomplete
    # Review fix D: an incomplete line carries no value, not a zero-assumed one.
    for line in ("product_cost", "contribution_before_marketing",
                 "contribution_after_marketing", "margin_pct"):
        assert p[line].value is None, line
    assert p["net_revenue"].value == 200
    # A plain SUM() would have reported €40 of product cost as if it were complete.
    contrib = measure.contribution_between(conn, LUNA, "2026-08-01", "2026-08-31")
    assert contrib.incomplete


def test_30_store_contribution_never_enters_an_action_benefit(conn):
    action = add_action(conn, comparison="holdout", window_start="2026-06-01",
                        window_end="2026-06-10", post_period_days=0)
    assign_customers(conn, action, ["T1", "T2"], ["C1", "C2"])
    add_order(conn, "2026-06-03", "T1")
    before = measure.holdout_benefit(conn, LUNA, action, "2026-06-01", "2026-06-10").benefit_eur
    for i in range(20):                       # the store has a great month anyway
        add_order(conn, "2026-06-05", f"walk-in-{i}", revenue=500)
    after = measure.holdout_benefit(conn, LUNA, action, "2026-06-01", "2026-06-10").benefit_eur
    assert before == after


def test_41_where_to_grow_lists_only_matching_suitable_measurable_plans(conn):
    _months_of_orders(conn, {"2026-07": (20, 40), "2026-08": (20, 40), "2026-09": (20, 40),
                             "2026-10": (12, 40)})   # orders fall 40%
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (LUNA,)).fetchone()
    grow = {w["metric"]: w for w in measure.where_to_grow(conn, client, "2026-10")}
    assert "orders" not in grow or all(p["data_fit"] != "no" for p in grow["orders"]["plans"])
    assert "average_order_value" not in grow          # unchanged: within tolerance
    for w in grow.values():
        for p in w["plans"]:
            tags = {r[0] for r in conn.execute(
                "SELECT value FROM plan_template_tags WHERE plan_template_id = ? AND kind = 'moves'",
                (p["id"],))}
            assert w["metric"] in tags and p["data_fit"] != "no"
            models = {r[0] for r in conn.execute(
                """SELECT value FROM plan_template_tags WHERE plan_template_id = ?
                   AND kind = 'business_model'""", (p["id"],))}
            assert not models or "dtc" in models      # B2B-only plans never shown to a DTC store


def test_42_refunds_after_the_measurement_period_never_change_a_result(conn):
    action = add_action(conn, comparison="holdout", window_start="2026-06-01",
                        window_end="2026-06-10", post_period_days=0)
    assign_customers(conn, action, ["T1"], ["C1"])
    order = add_order(conn, "2026-06-05", "T1")
    before = measure.holdout_benefit(conn, LUNA, action, "2026-06-01", "2026-06-10").benefit_eur
    add_refund(conn, order, "2026-06-25", 100)        # after the period ends
    after = measure.holdout_benefit(conn, LUNA, action, "2026-06-01", "2026-06-10").benefit_eur
    assert before == after
    assert measure.growth_pnl(conn, LUNA, "2026-06")["refunds"].value == 100   # still in its month
