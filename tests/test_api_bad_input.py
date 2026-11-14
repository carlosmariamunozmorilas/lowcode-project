"""Session 4 lab, Block 2: send the signed webhook bad input and check it is refused
with a 4xx and a reason, never a 500, and that nothing reaches the shop tables.

Every request here is correctly signed, so it gets past authentication and the
bad input itself is what the handler has to deal with.
"""

import hashlib
import hmac
import json

import pytest

from conftest import LUNA, SECRETS

from test_api import batch, count


def send(client, raw: bytes, automation: str = "shop_intake"):
    signature = hmac.new(SECRETS[automation].encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/api/events", data=raw, content_type="application/json",
                       headers={"X-Automation": automation, "X-Signature": signature})


def body(**changes) -> bytes:
    event = batch()
    for key, value in changes.items():
        if value is ...:
            event.pop(key)
        else:
            event[key] = value
    return json.dumps(event).encode()


def with_order(**changes) -> bytes:
    event = batch()
    event["orders"][0].update(changes)
    return json.dumps(event).encode()


SHOP_TABLES = ("orders", "refunds", "sessions", "ad_spend")

CASES = {
    # The body itself
    "empty body": b"",
    "not JSON": b"this is not json",
    "JSON list, not an object": b"[]",
    "JSON null": b"null",
    "JSON string": b'"shop_data"',
    "empty object": b"{}",
    # Missing or wrong fields
    "missing external_id": body(external_id=...),
    "missing client_id": body(client_id=...),
    "client_id as text": body(client_id=str(LUNA)),
    "event_type as a list": body(event_type=["shop_data"]),
    "orders as a number": body(orders=5),
    "an order that is not an object": body(orders=["x"], expected_rows=1),
    "refunds as a number": body(refunds=5),
    "a refund that is not an object": body(refunds=["x"]),
    "sessions as text": body(sessions="abc"),
    "ad_spend row that is not an object": body(ad_spend=[1]),
    # Malformed values
    "date that is not a date": with_order(ordered_at="yesterday"),
    "negative revenue": with_order(net_revenue_eur=-5),
    "revenue as text": with_order(net_revenue_eur="100"),
    "revenue NaN": body().replace(b"100.0", b"NaN"),
    # Very long values (limits: 100 characters for ids, 200 for other short text)
    "very long external_id": body(external_id="x" * 100_000),
    "external_id one over the limit": body(external_id="x" * 101),
    "very long customer_ref": with_order(customer_ref="c" * 100_000),
    "very long channel": with_order(channel="m" * 201),
}


@pytest.mark.parametrize("raw", CASES.values(), ids=CASES.keys())
def test_bad_input_is_refused_without_a_crash(client, app_conn, raw):
    before = {t: count(app_conn, t) for t in SHOP_TABLES}
    response = send(client, raw)
    assert 400 <= response.status_code < 500, (response.status_code, response.get_data()[:200])
    assert response.is_json and response.get_json().get("reason"), "a refusal must say why"
    assert {t: count(app_conn, t) for t in SHOP_TABLES} == before, "nothing may be written"


def test_values_at_the_limit_are_accepted(client):
    raw = body(external_id="x" * 100)
    raw = raw.replace(b'"C-1"', json.dumps("c" * 100).encode())
    assert send(client, raw).status_code == 201


REPORT_CASES = {
    "month as a number": {"month": 202610},
    "month null": {"month": None},
    "draft_text missing": {"draft_text": ...},
    "draft_text over 20,000 characters": {"draft_text": "d" * 20_001},
}


@pytest.mark.parametrize("change", REPORT_CASES.values(), ids=REPORT_CASES.keys())
def test_bad_report_draft_is_refused_without_a_crash(client, app_conn, change):
    event = {"event_type": "report_draft", "external_id": "R-1", "client_id": LUNA,
             "month": "2026-10", "draft_text": "October went well."}
    for key, value in change.items():
        if value is ...:
            event.pop(key)
        else:
            event[key] = value
    response = send(client, json.dumps(event).encode(), automation="report_draft")
    assert 400 <= response.status_code < 500, (response.status_code, response.get_data()[:200])
    assert count(app_conn, "client_reports") == 0


def test_oversized_body_is_refused(client):
    raw = body(orders=[{"pad": "x" * 2_100_000}], expected_rows=1)
    assert send(client, raw).status_code == 413
