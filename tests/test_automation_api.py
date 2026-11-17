"""The reads the Make automations use, and the outbox that rings their doorbell."""

import hashlib
import hmac
import json
import urllib.error
from datetime import date

import outbox
from conftest import (CONSULTANT, LEAD_A, LUNA, OTHER, SECRETS, add_action, ready_action,
                      signed)
from routes.api import business_days_between


def read(client, url, automation):
    """A signed GET: the signature covers the path and query, as Make sends it."""
    return signed(client, url, {}, automation=automation, method="get")


def test_a_read_signature_cannot_be_reused_for_another_client(client):
    good = hmac.new(SECRETS["below_target_alert"].encode(), f"/api/alerts?client_id={LUNA}".encode(),
                    hashlib.sha256).hexdigest()
    headers = {"X-Automation": "below_target_alert", "X-Signature": good}
    assert client.get(f"/api/alerts?client_id={LUNA}", headers=headers).status_code == 200
    assert client.get(f"/api/alerts?client_id={OTHER}", headers=headers).status_code == 401


def add_component_month(conn, benefit, cost, month="2026-10", hours=0.0, name="Flow"):
    component = conn.execute(
        """INSERT INTO components (client_id, name, discipline, lifecycle_stage, benefit_type,
               measurement, started_on) VALUES (?, ?, 'automations', 'conversion',
               'contribution', 'holdout_kept', '2026-07-01')""", (LUNA, name)).lastrowid
    conn.execute(
        """INSERT INTO component_months (component_id, client_id, month, operating_cost_eur,
               operating_hours, measured_benefit_eur, confidence, benefit_key, recorded_by)
           VALUES (?, ?, ?, ?, ?, ?, 'holdout', ?, ?)""",
        (component, LUNA, month, cost, hours, benefit, f"luna:{name}", CONSULTANT))
    conn.commit()
    return component


def history(conn, action_id, to_status, when):
    conn.execute("""INSERT INTO action_history (action_id, from_status, to_status, actor_id,
                        created_at) VALUES (?, NULL, ?, ?, ?)""",
                 (action_id, to_status, CONSULTANT, when))
    conn.commit()


# --- /api/clients ----------------------------------------------------------------

def test_clients_lists_active_clients_for_any_signed_automation(client, app_conn):
    app_conn.execute("UPDATE clients SET is_active = 0 WHERE id = ?", (OTHER,))
    app_conn.commit()
    body = read(client, "/api/clients", "shop_intake").get_json()
    assert [(c["id"], c["name"]) for c in body["clients"]] == [(LUNA, "Luna Test")]
    assert body["last_month"] == "2026-10"          # TODAY is 2026-11-02 in the fixture
    assert client.get("/api/clients").status_code == 401


def test_clients_tell_the_intake_which_days_are_missing(client, app_conn):
    app_conn.execute("INSERT INTO sessions (client_id, date, channel, sessions) "
                     "VALUES (?, '2026-10-30', 'meta', 10)", (LUNA,))
    app_conn.commit()
    luna, other = read(client, "/api/clients", "shop_intake").get_json()["clients"]
    assert (luna["next_day"], luna["days_behind"]) == ("2026-10-31", 2)    # 31 Oct and 1 Nov
    assert (other["next_day"], other["days_behind"]) == ("2026-11-01", 1)  # no data yet


# --- /api/alerts -----------------------------------------------------------------

def test_alerts_flag_a_component_and_the_system_below_target(client, app_conn):
    add_component_month(app_conn, benefit=110, cost=100)     # ROI 10% against a 20% target
    body = read(client, f"/api/alerts?client_id={LUNA}", "below_target_alert").get_json()
    assert body["month"] == "2026-10"                         # the latest month with results
    kinds = {f["kind"]: f for f in body["flags"]}
    assert set(kinds) == {"system_below_target", "component_below_target"}
    assert kinds["system_below_target"]["external_id"] == f"alert:{LUNA}:system:2026-10"
    assert body["recipients"] == [f"user{CONSULTANT}@test.example"]


def test_alerts_stay_quiet_when_on_target(client, app_conn):
    add_component_month(app_conn, benefit=200, cost=100)     # ROI 100%
    body = read(client, f"/api/alerts?client_id={LUNA}", "below_target_alert").get_json()
    assert body["flags"] == []


def test_alerts_flag_an_ended_window_with_no_result_once(client, app_conn):
    ended = ready_action(app_conn, status="approved", window_start="2026-09-01",
                         window_end="2026-09-28", post_period_days=14)   # over on 12 October
    ready_action(app_conn, status="approved", window_start="2026-10-20",
                 window_end="2026-11-10", post_period_days=0)            # still running
    app_conn.commit()
    flags = read(client, f"/api/alerts?client_id={LUNA}", "below_target_alert").get_json()["flags"]
    assert [(f["kind"], f["item_id"]) for f in flags] == [("window_ended", ended)]
    assert flags[0]["external_id"] == f"alert:{LUNA}:action:{ended}:window_ended"


def test_alerts_refuse_wrong_scope_bad_month_and_unknown_client(client):
    assert read(client, f"/api/alerts?client_id={LUNA}", "shop_intake").status_code == 403
    assert read(client, f"/api/alerts?client_id={LUNA}&month=oct",
                "below_target_alert").status_code == 400
    assert read(client, "/api/alerts?client_id=999", "below_target_alert").status_code == 404


# --- /api/reviews and /api/actions/<id> ---------------------------------------------

def test_business_days_skip_weekends():
    assert business_days_between(date(2026, 10, 30), date(2026, 11, 2)) == 1   # Fri → Mon
    assert business_days_between(date(2026, 11, 2), date(2026, 11, 2)) == 0


def test_reviews_list_only_actions_waiting_long_enough(client, app_conn):
    old = ready_action(app_conn, status="in_review")
    new = ready_action(app_conn, status="in_review")
    history(app_conn, old, "in_review", "2026-10-28T09:00:00Z")    # Wed → Mon: 3 business days
    history(app_conn, new, "in_review", "2026-10-30T09:00:00Z")    # Fri → Mon: 1
    body = read(client, "/api/reviews?min_business_days=2", "approval_routing").get_json()
    assert [a["id"] for a in body["actions"]] == [old]
    assert body["actions"][0]["reviewer"]["email"] == f"user{LEAD_A}@test.example"
    assert len(read(client, "/api/reviews", "approval_routing").get_json()["actions"]) == 2


def test_action_detail_names_requester_and_reviewer(client, app_conn):
    action = ready_action(app_conn, status="in_review")
    history(app_conn, action, "in_review", "2026-11-01T09:00:00Z")
    body = read(client, f"/api/actions/{action}", "approval_routing").get_json()
    assert body["requester"]["email"] == f"user{CONSULTANT}@test.example"
    assert body["reviewer"]["email"] == f"user{LEAD_A}@test.example"
    assert body["last_change"]["to_status"] == "in_review"
    assert read(client, "/api/actions/999", "approval_routing").status_code == 404


def test_only_the_routing_automation_reads_reviews(client):
    for automation in ("shop_intake", "below_target_alert", "report_draft"):
        assert read(client, "/api/reviews", automation).status_code == 403
    assert read(client, f"/api/metrics?client_id={LUNA}&month=2026-10",
                "approval_routing").status_code == 403


# --- /api/metrics additions -----------------------------------------------------------

def test_metrics_carry_closed_actions_and_alerts_but_no_emails(client, app_conn):
    action = add_action(app_conn, status="closed", decision="adopt", confidence="holdout",
                        measured_benefit_eur=900.0)
    history(app_conn, action, "closed", "2026-10-15T09:00:00Z")
    app_conn.execute(
        """INSERT INTO automation_events (source, client_id, event_type, external_id, payload,
               status, received_at) VALUES ('below_target_alert', ?, 'alerts', 'a1', ?,
               'accepted', '2026-10-20T06:00:00Z')""",
        (LUNA, json.dumps({"message": "Below target"})))
    app_conn.commit()
    body = read(client, f"/api/metrics?client_id={LUNA}&month=2026-10", "report_draft").get_json()
    assert [(a["id"], a["confidence"]) for a in body["actions_closed"]] == [(action, "holdout")]
    assert body["alerts_raised"] == ["Below target"]
    assert "@" not in json.dumps(body)              # it goes into an AI prompt


# --- the outbox -------------------------------------------------------------------------

def announce(conn, event_type, entity_id=None):
    conn.execute("INSERT INTO outbound_events (event_type, client_id, entity_id) VALUES (?, ?, ?)",
                 (event_type, LUNA, entity_id))
    conn.commit()


def undelivered(conn):
    return [r[0] for r in conn.execute(
        "SELECT event_type FROM outbound_events WHERE delivered_at IS NULL ORDER BY id")]


def test_outbox_sends_ids_only_signed_and_marks_delivered(app_conn):
    announce(app_conn, "action.review_requested", 7)
    sent = []
    hooks = {"action.review_requested": "https://hook.example/a"}
    assert outbox.dispatch(app_conn, hooks, "s3cret",
                           send=lambda url, body, sig: sent.append((url, body, sig)) or True) == 1
    url, body, sig = sent[0]
    assert json.loads(body) == {"id": 1, "event_type": "action.review_requested",
                                "client_id": LUNA, "entity_id": 7}
    assert sig == hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert undelivered(app_conn) == []


def test_outbox_keeps_rows_when_make_is_down_or_not_listening(app_conn):
    announce(app_conn, "action.closed")          # no scenario listens: stays, does not block
    announce(app_conn, "data.loaded")
    announce(app_conn, "data.loaded")

    def down(url, body, sig):
        raise urllib.error.URLError("unreachable")

    hooks = {"data.loaded": "https://hook.example/d"}
    assert outbox.dispatch(app_conn, hooks, "", send=down) == 0
    assert undelivered(app_conn) == ["action.closed", "data.loaded", "data.loaded"]
    assert outbox.dispatch(app_conn, hooks, "", send=lambda *a: True) == 2
    assert undelivered(app_conn) == ["action.closed"]


def test_an_accepted_batch_rings_the_doorbell_after_the_response(app, client, app_conn):
    calls = []
    app.config["MAKE_WEBHOOKS"] = {"data.loaded": "https://hook.example/d"}
    original = outbox.post_json
    outbox.post_json = lambda url, body, sig: calls.append(url) or True
    try:
        rows = [{"external_id": "O-1", "ordered_at": "2026-11-01T10:00:00Z",
                 "customer_ref": "C-1", "channel": "meta", "net_revenue_eur": 10.0}]
        batch = {"event_type": "shop_data", "external_id": "L-2026-11-01", "client_id": LUNA,
                 "expected_rows": 1, "expected_revenue_eur": 10.0, "orders": rows}
        assert signed(client, "/api/events", batch).status_code == 201
    finally:
        outbox.post_json = original
    assert calls == ["https://hook.example/d"]
    assert undelivered(app_conn) == []
