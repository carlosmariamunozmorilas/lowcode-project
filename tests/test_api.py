"""The signed API: spec v2 §11 tests 18–20, 27, 36."""

from conftest import INTAKE, LUNA, REPORTER, signed


def batch(external_id="L-2026-10-01", rows=None, expected_rows=None, expected_revenue=None,
          refunds=None):
    rows = rows if rows is not None else [
        {"external_id": "O-1", "ordered_at": "2026-10-01T10:00:00Z", "customer_ref": "C-1",
         "channel": "meta", "net_revenue_eur": 100.0, "product_cost_eur": 40,
         "shipping_cost_eur": 5, "payment_fee_eur": 2},
        {"external_id": "O-2", "ordered_at": "2026-10-01T11:00:00Z", "customer_ref": "C-2",
         "channel": "meta", "net_revenue_eur": 50.5, "product_cost_eur": 20,
         "shipping_cost_eur": 5, "payment_fee_eur": 1},
    ]
    return {"event_type": "shop_data", "external_id": external_id, "client_id": LUNA,
            "expected_rows": len(rows) if expected_rows is None else expected_rows,
            "expected_revenue_eur": sum(r["net_revenue_eur"] for r in rows)
            if expected_revenue is None else expected_revenue,
            "orders": rows, "refunds": refunds or []}


def count(app_conn, table):
    return app_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_18_refuses_missing_header_unknown_name_or_bad_signature(client, app_conn):
    assert client.post("/api/events", json=batch()).status_code == 401
    assert signed(client, "/api/events", batch(), automation="nobody",
                  secret="x").status_code == 401
    assert signed(client, "/api/events", batch(), secret="wrong").status_code == 401
    app_conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (INTAKE,))
    app_conn.commit()
    assert signed(client, "/api/events", batch()).status_code == 401
    assert count(app_conn, "orders") == 0 and count(app_conn, "automation_events") == 0


def test_18b_accepts_a_valid_batch_once_and_records_its_automation(client, app_conn):
    assert signed(client, "/api/events", batch()).status_code == 201
    event = app_conn.execute("SELECT * FROM automation_events").fetchone()
    assert event["source"] == "shop_intake" and event["status"] == "accepted"
    assert count(app_conn, "orders") == 2
    assert app_conn.execute("SELECT event_type FROM outbound_events").fetchone()[0] == "data.loaded"
    again = signed(client, "/api/events", batch())
    assert again.status_code == 200 and again.get_json()["status"] == "duplicate"
    assert count(app_conn, "orders") == 2
    statuses = [r[0] for r in app_conn.execute("SELECT status FROM automation_events ORDER BY id")]
    assert statuses == ["accepted", "duplicate"]


def test_review_b_a_racing_copy_is_a_duplicate_not_a_crash(app, app_conn):
    """Review fix B: two copies racing past the duplicate check used to end in a 500.

    The race itself cannot be timed in a test, so this reproduces its last
    step: the losing copy tries to record a rejection for an external id that
    the winning copy has already recorded as accepted."""
    from db import get_db
    from routes import api

    app_conn.execute(
        """INSERT INTO automation_events (source, client_id, event_type, external_id, payload,
               status) VALUES ('shop_intake', ?, 'shop_data', 'L-race', '{}', 'accepted')""",
        (LUNA,))
    app_conn.commit()
    with app.test_request_context():
        response, status = api._reject(get_db(), "shop_intake", LUNA, "shop_data", "L-race",
                                       {}, "UNIQUE constraint failed: orders.external_id", 422)
        assert status == 200 and response.get_json()["status"] == "duplicate"
    statuses = [r[0] for r in app_conn.execute(
        "SELECT status FROM automation_events WHERE external_id = 'L-race' ORDER BY id")]
    assert statuses == ["accepted", "duplicate"]


def test_19_unknown_order_or_client_is_refused(client, app_conn):
    bad_refund = batch(refunds=[{"external_id": "R-1", "order_external_id": "NOPE",
                                 "refunded_at": "2026-10-02", "amount_eur": 10}])
    assert signed(client, "/api/events", bad_refund).status_code == 422
    assert count(app_conn, "orders") == 0           # the whole batch rolled back
    unknown = {**batch("x2"), "client_id": 999}
    assert signed(client, "/api/events", unknown).status_code == 422


def test_27_control_totals_reject_the_whole_batch(client, app_conn):
    off_by_a_cent = batch("b1", expected_revenue=150.49)
    response = signed(client, "/api/events", off_by_a_cent)
    assert response.status_code == 422
    assert "control total" in response.get_json()["reason"]
    assert signed(client, "/api/events", batch("b2", expected_rows=3)).status_code == 422
    rows = batch()["orders"]
    invalid = batch("b3", rows=[rows[0], {**rows[1], "net_revenue_eur": -5}],
                    expected_revenue=95.0)
    assert signed(client, "/api/events", invalid).status_code == 422
    assert count(app_conn, "orders") == 0
    rejected = app_conn.execute(
        "SELECT reason FROM automation_events WHERE status = 'rejected'").fetchall()
    assert len(rejected) == 3 and all(r["reason"] for r in rejected)


def test_27b_missing_costs_stay_missing(client, app_conn):
    rows = batch()["orders"]
    rows[0] = {**rows[0], "product_cost_eur": None}
    assert signed(client, "/api/events", batch("m1", rows=rows)).status_code == 201
    assert app_conn.execute(
        "SELECT COUNT(*) FROM orders WHERE product_cost_eur IS NULL").fetchone()[0] == 1


def test_20_metrics_are_aggregates_only(client):
    signed(client, "/api/events", batch())
    response = signed(client, "/api/metrics?client_id=1&month=2026-10", {}, automation="report_draft",
                      method="get")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "C-1" not in text and "O-1" not in text
    assert response.get_json()["growth_pnl"]["net_revenue"]["value"] == 150.5


def test_36_report_automation_scope(client, app_conn):
    draft = {"event_type": "report_draft", "external_id": "r-2026-10", "client_id": LUNA,
             "month": "2026-10", "draft_text": "October went well.", "model": "m",
             "prompt_version": "v1", "generation_cost_eur": 0.02}
    assert signed(client, "/api/events", draft, automation="report_draft").status_code == 201
    assert app_conn.execute("SELECT reviewed_by FROM client_reports").fetchone()[0] is None
    assert signed(client, "/api/events", batch(), automation="report_draft").status_code == 403
    assert signed(client, "/api/events", draft).status_code == 403   # intake may not draft
    metrics = signed(client, "/api/metrics?client_id=1&month=2026-10", {}, method="get")
    assert metrics.status_code == 403                                # intake may not read
    assert REPORTER  # the report automation's service user exists in the fixture
