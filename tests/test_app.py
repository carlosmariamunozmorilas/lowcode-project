"""Routes, access and the workflow end to end: spec v2 §11 tests 13–15, 17, 21, 34, 35, 38."""

import pytest

import routes.actions
from conftest import (CONSULTANT, INTAKE, LEAD_A, LEAD_B, LUNA, OTHER, OTHER_CONSULTANT, PASSWORD,
                      add_action, login, post, ready_action)


def test_sign_in_and_out(client):
    page = client.get("/login")
    with client.session_transaction() as s:
        token = s["csrf"]
    assert b"Sign in" in page.data
    bad = client.post("/login", data={"csrf_token": token, "email": "user4@test.example",
                                      "password": "wrong"})
    assert bad.status_code == 401
    good = client.post("/login", data={"csrf_token": token, "email": "user4@test.example",
                                       "password": PASSWORD})
    assert good.status_code == 302


def test_21_a_service_account_cannot_sign_in(client):
    client.get("/login")
    with client.session_transaction() as s:
        token = s["csrf"]
    response = client.post("/login", data={"csrf_token": token,
                                           "email": "shop_intake@test.example", "password": ""})
    assert response.status_code == 401
    login(client, INTAKE)            # even a forged session gives it nothing
    assert client.get("/").status_code == 302


def test_43_forms_without_the_csrf_token_are_refused(client, app_conn):
    login(client, CONSULTANT)
    action = add_action(app_conn)
    app_conn.commit()
    response = client.post(f"/actions/{action}/cancel", data={})
    assert response.status_code == 400


@pytest.mark.parametrize("url", ["/clients/1", "/clients/1/details", "/clients/1/plans",
                                 "/clients/1/reports/2026-10", "/actions/{a}",
                                 "/clients/1/actions/new"])
def test_13_another_clients_pages_are_404(client, app_conn, url):
    action = add_action(app_conn)
    app_conn.commit()
    login(client, OTHER_CONSULTANT)          # assigned to the other store only
    assert client.get(url.format(a=action)).status_code == 404


def test_13b_admin_reads_every_client_but_cannot_change_one(client, app_conn):
    action = ready_action(app_conn)
    app_conn.commit()
    login(client, 1)
    assert client.get("/clients/1").status_code == 200
    assert post(client, f"/actions/{action}/cancel").status_code == 404


def test_14_reviewer_must_be_one_of_the_clients_leads(client, app_conn):
    action = add_action(app_conn)
    app_conn.execute("DELETE FROM client_assignments WHERE user_id = ? AND client_id = ?",
                     (LEAD_A, LUNA))
    app_conn.commit()
    login(client, CONSULTANT)
    post(client, f"/actions/{action}/assign", {"owner_id": CONSULTANT, "reviewer_id": LEAD_A})
    row = app_conn.execute("SELECT status, reviewer_id FROM actions WHERE id = ?",
                           (action,)).fetchone()
    assert row["status"] == "submitted" and row["reviewer_id"] is None
    post(client, f"/actions/{action}/assign", {"owner_id": CONSULTANT, "reviewer_id": LEAD_B})
    row = app_conn.execute("SELECT status, reviewer_id FROM actions WHERE id = ?",
                           (action,)).fetchone()
    assert row["status"] == "assigned" and row["reviewer_id"] == LEAD_B


def test_15_mass_assignment_is_ignored(client, app_conn):
    action = add_action(app_conn)
    app_conn.commit()
    login(client, CONSULTANT)
    post(client, f"/actions/{action}/edit", {"title": "Renamed", "status": "closed",
                                              "measured_benefit_eur": "99999",
                                              "decision": "adopt", "client_id": "2"})
    row = app_conn.execute("SELECT * FROM actions WHERE id = ?", (action,)).fetchone()
    assert row["title"] == "Renamed"
    assert row["status"] == "submitted" and row["measured_benefit_eur"] is None
    assert row["decision"] is None and row["client_id"] == LUNA


def test_full_workflow_writes_history_and_outbox(client, app_conn):
    action = ready_action(app_conn, status="assigned")
    app_conn.commit()
    login(client, CONSULTANT)
    post(client, f"/actions/{action}/review")
    login(client, LEAD_A)
    post(client, f"/actions/{action}/approve")
    row = app_conn.execute("SELECT status FROM actions WHERE id = ?", (action,)).fetchone()
    assert row["status"] == "approved"
    steps = [r["to_status"] for r in app_conn.execute(
        "SELECT to_status FROM action_history WHERE action_id = ? ORDER BY id", (action,))]
    assert steps == ["in_review", "approved"]
    events = [r["event_type"] for r in app_conn.execute("SELECT event_type FROM outbound_events")]
    assert events == ["action.review_requested", "action.approved"]


def test_frozen_fields_cannot_be_edited_in_review(client, app_conn):
    action = ready_action(app_conn, status="in_review")
    app_conn.commit()
    login(client, CONSULTANT)
    response = post(client, f"/actions/{action}/edit", {"hurdle_eur": "1"})
    assert response.status_code == 400
    assert app_conn.execute("SELECT hurdle_eur FROM actions WHERE id = ?",
                            (action,)).fetchone()[0] == 500


def test_46d_channel_scope_must_be_one_of_the_clients_channels(client, app_conn):
    app_conn.execute("""INSERT INTO sessions (client_id, date, channel, sessions)
                        VALUES (?, '2026-06-01', 'google_search', 10)""", (LUNA,))
    action = add_action(app_conn, comparison="before_after")
    app_conn.commit()
    login(client, CONSULTANT)
    unknown = post(client, f"/actions/{action}/edit", {"scope_channel": "tiktok"})
    assert unknown.status_code == 400
    known = post(client, f"/actions/{action}/edit", {"scope_channel": "google_search"})
    assert known.status_code == 302
    assert app_conn.execute("SELECT scope_channel FROM actions WHERE id = ?",
                            (action,)).fetchone()[0] == "google_search"


def test_17_status_change_and_history_are_one_transaction(client, app_conn, monkeypatch):
    action = add_action(app_conn)
    app_conn.commit()

    def broken(*args, **kwargs):
        raise RuntimeError("history write failed")

    monkeypatch.setattr(routes.actions, "record", broken)
    login(client, CONSULTANT)
    with pytest.raises(RuntimeError):
        post(client, f"/actions/{action}/cancel")
    assert app_conn.execute("SELECT status FROM actions WHERE id = ?",
                            (action,)).fetchone()[0] == "submitted"


def test_only_featured_plans_start_an_action(client):
    login(client, CONSULTANT)
    assert client.get("/clients/1/actions/new?plan=65").status_code == 200
    assert client.get("/clients/1/actions/new?plan=8").status_code == 302


def _component(app_conn, measurement="holdout_kept", benefit_type="contribution", origin=None):
    cur = app_conn.execute(
        """INSERT INTO components (client_id, origin_action_id, name, discipline, lifecycle_stage,
               benefit_type, measurement, started_on, benefit_key)
           VALUES (?, ?, 'Comp', 'automations', 'conversion', ?, ?, '2026-07-01', 'k')""",
        (LUNA, origin, benefit_type, measurement))
    app_conn.commit()
    return cur.lastrowid


def test_38_a_typed_benefit_is_ignored_when_the_app_computes_it(client, app_conn):
    component = _component(app_conn)
    login(client, CONSULTANT)
    post(client, f"/components/{component}/months",
         {"month": "2026-08", "operating_cost_eur": "100", "measured_benefit_eur": "99999"})
    row = app_conn.execute("SELECT * FROM component_months").fetchone()
    assert row["measured_benefit_eur"] != 99999
    assert row["recorded_by"] == CONSULTANT


def test_38b_owner_of_the_origin_action_cannot_record_an_invoice_month(client, app_conn):
    origin = add_action(app_conn, benefit_type="avoided_cost", comparison="invoice",
                        requester_id=CONSULTANT, owner_id=LEAD_A, status="closed")
    component = _component(app_conn, "invoice", "avoided_cost", origin)
    login(client, LEAD_A)                     # owned the origin action
    post(client, f"/components/{component}/months",
         {"month": "2026-08", "measured_benefit_eur": "650"})
    assert app_conn.execute("SELECT COUNT(*) FROM component_months").fetchone()[0] == 0
    login(client, LEAD_B)                     # independent assigned lead
    post(client, f"/components/{component}/months",
         {"month": "2026-08", "measured_benefit_eur": "650"})
    row = app_conn.execute("SELECT * FROM component_months").fetchone()
    assert row["measured_benefit_eur"] == 650 and row["confidence"] == "documented"


def test_review_a_second_component_sharing_a_key_records_its_cost(client, app_conn):
    """Review fix A: the month used to be refused, losing its cost and hours."""
    from conftest import add_order, assign_customers
    pilot = add_action(app_conn, comparison="holdout", status="closed")
    assign_customers(app_conn, pilot, ["T1", "T2"], ["C1", "C2"], day="2026-08-03")
    add_order(app_conn, "2026-08-10", "T1")
    first = _component(app_conn, origin=pilot)
    second = _component(app_conn, origin=pilot)
    login(client, CONSULTANT)
    post(client, f"/components/{first}/months", {"month": "2026-08", "operating_cost_eur": "100"})
    post(client, f"/components/{second}/months", {"month": "2026-08", "operating_cost_eur": "60"})
    rows = app_conn.execute(
        "SELECT component_id, operating_cost_eur, measured_benefit_eur FROM component_months "
        "ORDER BY component_id").fetchall()
    assert [r["component_id"] for r in rows] == [first, second]
    assert rows[1]["operating_cost_eur"] == 60 and rows[1]["measured_benefit_eur"] is None
    assert rows[0]["measured_benefit_eur"] is not None


def test_review_c_reactivated_component_has_no_retirement_date(client, app_conn):
    component = _component(app_conn)
    login(client, LEAD_A)
    post(client, f"/components/{component}/status", {"status": "retired"})
    assert app_conn.execute("SELECT retired_on FROM components WHERE id = ?",
                            (component,)).fetchone()[0] is not None
    post(client, f"/components/{component}/status", {"status": "running"})
    row = app_conn.execute("SELECT status, retired_on FROM components WHERE id = ?",
                           (component,)).fetchone()
    assert row["status"] == "running" and row["retired_on"] is None


def _draft(app_conn, month="2026-10", cost=0.02):
    app_conn.execute("""INSERT INTO client_reports (client_id, month, draft_text, model,
                            prompt_version, generation_cost_eur)
                        VALUES (?, ?, 'Draft text', 'model-x', 'v1', ?)""", (LUNA, month, cost))
    app_conn.commit()


def test_34_report_needs_a_person_and_a_reason_to_reject(client, app_conn):
    _draft(app_conn)
    login(client, CONSULTANT)
    post(client, "/clients/1/reports/2026-10", {"decision": "reject", "rejection_reason": ""})
    assert app_conn.execute("SELECT status FROM client_reports").fetchone()[0] == "draft"
    post(client, "/clients/1/reports/2026-10", {"decision": "reject",
                                                "rejection_reason": "Wrong month's figures"})
    row = app_conn.execute("SELECT * FROM client_reports").fetchone()
    assert row["status"] == "rejected" and row["reviewed_by"] == CONSULTANT
    _draft(app_conn)                          # a new draft for the month is now allowed
    assert app_conn.execute("SELECT COUNT(*) FROM client_reports").fetchone()[0] == 2


def test_35_report_quality_and_the_ai_label(client, app_conn):
    _draft(app_conn, "2026-09", 0.03)
    _draft(app_conn, "2026-10", 0.01)
    login(client, CONSULTANT)
    post(client, "/clients/1/reports/2026-09", {"decision": "send", "final_text": "Corrected text"})
    post(client, "/clients/1/reports/2026-10", {"decision": "send", "final_text": "Draft text"})
    rows = app_conn.execute("SELECT month, was_corrected FROM client_reports ORDER BY month").fetchall()
    assert [r["was_corrected"] for r in rows] == [1, 0]
    page = client.get("/clients/1/reports/2026-09").data.decode()
    assert "AI-assisted report: drafted with AI assistance and reviewed by a person" in page
    assert "correction rate 50%" in page and "cost per draft €0.02" in page


def test_dashboard_and_pages_render(client, app_conn):
    from conftest import add_order
    add_order(app_conn, "2026-10-03", "A")
    app_conn.commit()
    login(client, LEAD_A)
    for url in ("/", "/clients/1", "/clients/1/details", "/clients/1/plans", "/review",
                "/clients/1/reports/2026-10"):
        assert client.get(url).status_code == 200, url
    login(client, 1)
    assert client.get("/admin/clients").status_code == 200
    assert client.get("/admin/users").status_code == 200
    login(client, CONSULTANT)
    assert client.get("/admin/users").status_code == 403
    assert client.get("/review").status_code == 403


def test_no_result_is_shown_before_the_window_starts(client, app_conn):
    """Regression (found in the browser, 2 November): a pilot starting next week showed
    'So far: −€26,346' — an empty future period against the month before it."""
    from conftest import add_order
    add_order(app_conn, "2026-10-20", "A", revenue=500)
    action = ready_action(app_conn, comparison="before_after", window_start="2026-11-09",
                          window_end="2026-12-06", status="approved")
    app_conn.commit()
    login(client, LEAD_A)
    page = client.get(f"/actions/{action}").data.decode()
    assert "no result before then" in page and "So far" not in page


def test_deactivated_client_leaves_the_portfolio(client, app_conn):
    app_conn.execute("UPDATE clients SET is_active = 0 WHERE id = ?", (OTHER,))
    app_conn.commit()
    login(client, LEAD_B)
    page = client.get("/").data.decode()
    assert "Other Store" not in page and "Luna Test" in page
    assert client.get(f"/clients/{OTHER}").status_code == 404
