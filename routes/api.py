"""The signed API the Make automations use — and the only way they reach the app.

Every request names its automation in X-Automation and signs the raw body with
that automation's own secret in X-Signature (hex HMAC-SHA256). An unknown or
deactivated name, a missing secret or a bad signature is refused before
anything is read or written. Each automation may use only its own event types.

A shop-data batch is all or nothing: if its row count or revenue total misses
the control totals, or any row is invalid, no row is written and the event is
kept with its reason, so data-quality problems are counted, not lost.
"""

import hashlib
import hmac
import json
import math
import sqlite3

from flask import Blueprint, current_app, jsonify, request

import measure
from db import get_db, transaction

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_BODY_BYTES = 2_000_000


class Refused(Exception):
    def __init__(self, status: int, reason: str):
        super().__init__(reason)
        self.status = status
        self.reason = reason


def authenticate() -> tuple[sqlite3.Row, dict]:
    """The calling automation's service user and scope, or Refused."""
    from config import AUTOMATION_SCOPES

    name = request.headers.get("X-Automation", "")
    signature = request.headers.get("X-Signature", "")
    if not name or not signature:
        raise Refused(401, "X-Automation and X-Signature headers are required")
    user = get_db().execute(
        """SELECT * FROM users WHERE automation_name = ? AND is_service = 1 AND is_active = 1""",
        (name,)).fetchone()
    secret = current_app.config["AUTOMATION_SECRETS"].get(name)
    if user is None or secret is None or name not in AUTOMATION_SCOPES:
        raise Refused(401, "unknown automation")
    expected = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise Refused(401, "bad signature")
    return user, AUTOMATION_SCOPES[name]


@bp.errorhandler(Refused)
def refused(error: Refused):
    return jsonify({"status": "refused", "reason": error.reason}), error.status


def finite(value, name: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or value < minimum:
        raise ValueError(f"{name} must be a number of {minimum} or more")
    return float(value)


def text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def iso_date(value, name: str) -> str:
    value = text(value, name)
    if len(value) < 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"{name} must be an ISO date")
    return value


@bp.route("/events", methods=["POST"])
def events():
    user, scope = authenticate()
    if request.content_length and request.content_length > MAX_BODY_BYTES:
        raise Refused(413, "batch too large")
    try:
        event = json.loads(request.get_data() or b"{}")
    except ValueError:
        raise Refused(400, "body is not JSON") from None
    event_type = event.get("event_type")
    external_id = event.get("external_id")
    if event_type not in scope["events"]:
        raise Refused(403, f"this automation may not send '{event_type}'")
    if not isinstance(external_id, str) or not external_id:
        raise Refused(400, "external_id is required")

    conn = get_db()
    source = user["automation_name"]
    client_id = event.get("client_id")
    if conn.execute("""SELECT 1 FROM automation_events WHERE source = ? AND external_id = ?
                       AND status <> 'duplicate'""", (source, external_id)).fetchone():
        with transaction(conn):
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status, reason) VALUES (?, ?, ?, ?, '{}', 'duplicate',
                       'redelivered; nothing changed')""",
                (source, client_id if _client_exists(client_id) else None, event_type,
                 external_id))
        return jsonify({"status": "duplicate"}), 200
    if not _client_exists(client_id):
        return _reject(conn, source, None, event_type, external_id, event, "unknown client", 422)

    handler = {"shop_data": _shop_data, "alerts": _alert, "report_draft": _report_draft}
    return handler[event_type](conn, source, client_id, external_id, event)


def _client_exists(client_id) -> bool:
    return isinstance(client_id, int) and get_db().execute(
        "SELECT 1 FROM clients WHERE id = ? AND is_active = 1", (client_id,)).fetchone() is not None


def _reject(conn, source, client_id, event_type, external_id, event, reason, status, **totals):
    try:
        with transaction(conn):
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status, reason, expected_rows, parsed_rows, expected_revenue_eur,
                       parsed_revenue_eur) VALUES (?, ?, ?, ?, ?, 'rejected', ?, ?, ?, ?, ?)""",
                (source, client_id, event_type, external_id, json.dumps(event)[:20000], reason,
                 totals.get("expected_rows"), totals.get("parsed_rows"),
                 totals.get("expected_revenue"), totals.get("parsed_revenue")))
    except sqlite3.IntegrityError:
        # Two copies of the same event raced past the duplicate check and the
        # other one was recorded first: this one is a redelivery, not an error.
        # (Found by the 2 November code review: it used to end in an error 500.)
        with transaction(conn):
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status, reason) VALUES (?, ?, ?, ?, '{}', 'duplicate',
                       'redelivered while the first copy was being processed')""",
                (source, client_id, event_type, external_id))
        return jsonify({"status": "duplicate"}), 200
    return jsonify({"status": "rejected", "reason": reason}), status


def _shop_data(conn, source, client_id, external_id, event):
    orders = event.get("orders") or []
    refunds = event.get("refunds") or []
    sessions = event.get("sessions") or []
    spend = event.get("ad_spend") or []
    expected_rows = event.get("expected_rows")
    expected_revenue = event.get("expected_revenue_eur")
    totals = {"expected_rows": expected_rows if isinstance(expected_rows, int) else None,
              "expected_revenue": expected_revenue
              if isinstance(expected_revenue, (int, float)) else None,
              "parsed_rows": len(orders)}
    try:
        if not isinstance(orders, list) or not all(isinstance(o, dict) for o in orders):
            raise ValueError("orders must be a list of rows")
        parsed_revenue = round(sum(finite(o.get("net_revenue_eur"), "net_revenue_eur")
                                   for o in orders), 2)
        totals["parsed_revenue"] = parsed_revenue
        if totals["expected_rows"] is None or totals["expected_revenue"] is None:
            raise ValueError("control totals expected_rows and expected_revenue_eur are required")
        if len(orders) != expected_rows:
            raise ValueError(f"{len(orders)} order rows against a control total of {expected_rows}")
        if parsed_revenue != round(expected_revenue, 2):
            raise ValueError(f"revenue €{parsed_revenue:.2f} differs from the control total "
                             f"€{expected_revenue:.2f}")
        rows = []
        for o in orders:
            costs = []
            for name in ("product_cost_eur", "shipping_cost_eur", "payment_fee_eur"):
                # Missing stays missing (NULL): incomplete, never zero.
                costs.append(None if o.get(name) is None else finite(o[name], name))
            rows.append((client_id, text(o.get("external_id"), "external_id"),
                         iso_date(o.get("ordered_at"), "ordered_at"),
                         text(o.get("customer_ref"), "customer_ref"),
                         1 if o.get("is_new_customer") else 0, text(o.get("channel"), "channel"),
                         finite(o.get("net_revenue_eur"), "net_revenue_eur"),
                         finite(o.get("discount_eur", 0), "discount_eur"), *costs))
    except ValueError as error:
        return _reject(conn, source, client_id, "shop_data", external_id, event, str(error), 422,
                       **totals)

    try:
        with transaction(conn):
            conn.executemany(
                """INSERT INTO orders (client_id, external_id, ordered_at, customer_ref,
                       is_new_customer, channel, net_revenue_eur, discount_eur,
                       product_cost_eur, shipping_cost_eur, payment_fee_eur)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)
            for r in refunds:
                order = conn.execute(
                    "SELECT id FROM orders WHERE external_id = ? AND client_id = ?",
                    (text(r.get("order_external_id"), "order_external_id"), client_id)).fetchone()
                if order is None:
                    raise ValueError(f"refund for unknown order {r.get('order_external_id')}")
                conn.execute(
                    """INSERT INTO refunds (order_id, external_id, refunded_at, amount_eur,
                           restocked_cost_eur) VALUES (?, ?, ?, ?, ?)""",
                    (order["id"], text(r.get("external_id"), "external_id"),
                     iso_date(r.get("refunded_at"), "refunded_at"),
                     finite(r.get("amount_eur"), "amount_eur"),
                     finite(r.get("restocked_cost_eur", 0), "restocked_cost_eur")))
            for s in sessions:
                conn.execute(
                    "INSERT INTO sessions (client_id, date, channel, sessions) VALUES (?, ?, ?, ?)",
                    (client_id, iso_date(s.get("date"), "date"), text(s.get("channel"), "channel"),
                     int(finite(s.get("sessions"), "sessions"))))
            for a in spend:
                conn.execute(
                    "INSERT INTO ad_spend (client_id, date, channel, spend_eur) VALUES (?, ?, ?, ?)",
                    (client_id, iso_date(a.get("date"), "date"), text(a.get("channel"), "channel"),
                     finite(a.get("spend_eur"), "spend_eur")))
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status, expected_rows, parsed_rows, expected_revenue_eur,
                       parsed_revenue_eur) VALUES (?, ?, 'shop_data', ?, ?, 'accepted', ?, ?, ?, ?)""",
                (source, client_id, external_id, json.dumps({"rows": len(orders)}),
                 expected_rows, len(orders), expected_revenue, totals["parsed_revenue"]))
            conn.execute(
                "INSERT INTO outbound_events (event_type, client_id) VALUES ('data.loaded', ?)",
                (client_id,))
    except (ValueError, sqlite3.IntegrityError) as error:
        # The transaction rolled back: not one row of the batch was written.
        return _reject(conn, source, client_id, "shop_data", external_id, event, str(error), 422,
                       **totals)
    return jsonify({"status": "accepted", "rows": len(orders)}), 201


def _alert(conn, source, client_id, external_id, event):
    payload = {"metric": event.get("metric"), "message": str(event.get("message", ""))[:500]}
    with transaction(conn):
        conn.execute(
            """INSERT INTO automation_events (source, client_id, event_type, external_id,
                   payload, status) VALUES (?, ?, 'alerts', ?, ?, 'accepted')""",
            (source, client_id, external_id, json.dumps(payload)))
    return jsonify({"status": "accepted"}), 201


def _report_draft(conn, source, client_id, external_id, event):
    month = event.get("month", "")
    try:
        draft = text(event.get("draft_text"), "draft_text")
        if len(month) != 7 or month[4] != "-":
            raise ValueError("month must look like 2026-10")
        cost = event.get("generation_cost_eur")
        cost = None if cost is None else finite(cost, "generation_cost_eur")
        with transaction(conn):
            conn.execute(
                """INSERT INTO client_reports (client_id, month, draft_text, model,
                       prompt_version, generation_cost_eur) VALUES (?, ?, ?, ?, ?, ?)""",
                (client_id, month, draft, event.get("model"), event.get("prompt_version"), cost))
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status) VALUES (?, ?, 'report_draft', ?, ?, 'accepted')""",
                (source, client_id, external_id, json.dumps({"month": month})))
    except ValueError as error:
        return _reject(conn, source, client_id, "report_draft", external_id, event, str(error), 422)
    except sqlite3.IntegrityError:
        return _reject(conn, source, client_id, "report_draft", external_id, event,
                       "a report for this month is already waiting or sent", 409)
    return jsonify({"status": "accepted"}), 201


@bp.route("/metrics", methods=["GET"])
def metrics():
    """Aggregates for automations 2–4 — never order rows or customer references."""
    user, scope = authenticate()
    if not scope["metrics"]:
        raise Refused(403, "this automation may not read metrics")
    client_id = request.args.get("client_id", type=int)
    month = request.args.get("month", "")
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id = ? AND is_active = 1",
                          (client_id,)).fetchone()
    if client is None or len(month) != 7:
        raise Refused(404, "unknown client or month")
    pnl = measure.growth_pnl(conn, client_id, month)
    current = measure.store_metrics(conn, client_id, month)
    baseline = measure.baseline_metrics(conn, client_id, month)
    system = measure.system_month(conn, client, month)
    return jsonify({
        "client": {"id": client["id"], "name": client["name"],
                   "is_fictional": bool(client["is_fictional"]),
                   "roi_target": client["roi_target"]},
        "month": month,
        "growth_pnl": {k: {"value": v.value, "incomplete": v.incomplete}
                       for k, v in pnl.items() if k != "month"},
        "metrics": current,
        "baseline": baseline,
        "guardrails": [g.__dict__ for g in measure.guardrails(current, baseline)],
        "system": system.__dict__,
        "below_target": system.roi is not None and system.roi < client["roi_target"],
    })
