"""The signed API the Make automations use — and the only way they reach the app.

Every request names its automation in X-Automation and signs with that
automation's own secret in X-Signature (hex HMAC-SHA256): a POST signs its raw
body; a GET signs its path and query string (e.g. `/api/alerts?client_id=1`),
so a read's signature cannot be reused for another client. An unknown or
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

from datetime import date, timedelta

from flask import Blueprint, current_app, g, jsonify, request

import measure
import roi
from auth import today
from db import get_db, transaction

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_BODY_BYTES = 2_000_000
MAX_ID_CHARS = 100      # external ids and customer references
MAX_TEXT_CHARS = 200    # short text such as a channel name
MAX_DRAFT_CHARS = 20_000


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
    expected = hmac.new(secret.encode(), signed_message(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise Refused(401, "bad signature")
    return user, AUTOMATION_SCOPES[name]


def signed_message() -> bytes:
    """What the signature covers: a POST's raw body, a GET's path and query."""
    if request.method == "GET":
        query = request.query_string.decode()
        return (request.path + ("?" + query if query else "")).encode()
    return request.get_data()


@bp.errorhandler(Refused)
def refused(error: Refused):
    return jsonify({"status": "refused", "reason": error.reason}), error.status


def finite(value, name: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or value < minimum:
        raise ValueError(f"{name} must be a number of {minimum} or more")
    return float(value)


def text(value, name: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    if len(value.strip()) > max_chars:
        raise ValueError(f"{name} must be {max_chars} characters or fewer")
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
    if not isinstance(event, dict):
        raise Refused(400, "body must be a JSON object")
    event_type = event.get("event_type")
    external_id = event.get("external_id")
    if not isinstance(event_type, str):
        raise Refused(400, "event_type must be text")
    if event_type not in scope["events"]:
        raise Refused(403, f"this automation may not send '{event_type}'")
    if not isinstance(external_id, str) or not external_id:
        raise Refused(400, "external_id is required")
    if len(external_id) > MAX_ID_CHARS:
        raise Refused(400, f"external_id must be {MAX_ID_CHARS} characters or fewer")

    conn = get_db()
    source = user["automation_name"]
    client_id = event.get("client_id")
    if _already_accepted(conn, source, external_id):
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


def _already_accepted(conn, source, external_id) -> bool:
    # Only an accepted event holds its id. A rejected one stays on record with
    # its reason, but the corrected batch may be resent under the same id.
    return conn.execute("""SELECT 1 FROM automation_events WHERE source = ? AND external_id = ?
                           AND status = 'accepted'""", (source, external_id)).fetchone() is not None


def _reject(conn, source, client_id, event_type, external_id, event, reason, status, **totals):
    if _already_accepted(conn, source, external_id):
        # Two copies of the same event raced past the duplicate check and the
        # other one was accepted first: this one is a redelivery, not an error.
        # (Found by the 2 November code review: it used to end in an error 500.)
        with transaction(conn):
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status, reason) VALUES (?, ?, ?, ?, '{}', 'duplicate',
                       'redelivered while the first copy was being processed')""",
                (source, client_id, event_type, external_id))
        return jsonify({"status": "duplicate"}), 200
    with transaction(conn):
        conn.execute(
            """INSERT INTO automation_events (source, client_id, event_type, external_id,
                   payload, status, reason, expected_rows, parsed_rows, expected_revenue_eur,
                   parsed_revenue_eur) VALUES (?, ?, ?, ?, ?, 'rejected', ?, ?, ?, ?, ?)""",
            (source, client_id, event_type, external_id, json.dumps(event)[:20000], reason,
             totals.get("expected_rows"), totals.get("parsed_rows"),
             totals.get("expected_revenue"), totals.get("parsed_revenue")))
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
              "parsed_rows": len(orders) if isinstance(orders, list) else None}
    try:
        for name, given in (("orders", orders), ("refunds", refunds), ("sessions", sessions),
                            ("ad_spend", spend)):
            if not isinstance(given, list) or not all(isinstance(row, dict) for row in given):
                raise ValueError(f"{name} must be a list of rows")
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
            rows.append((client_id, text(o.get("external_id"), "external_id", MAX_ID_CHARS),
                         iso_date(o.get("ordered_at"), "ordered_at"),
                         text(o.get("customer_ref"), "customer_ref", MAX_ID_CHARS),
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
                    (text(r.get("order_external_id"), "order_external_id", MAX_ID_CHARS),
                     client_id)).fetchone()
                if order is None:
                    raise ValueError(f"refund for unknown order {r.get('order_external_id')}")
                conn.execute(
                    """INSERT INTO refunds (order_id, external_id, refunded_at, amount_eur,
                           restocked_cost_eur) VALUES (?, ?, ?, ?, ?)""",
                    (order["id"], text(r.get("external_id"), "external_id", MAX_ID_CHARS),
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
    g.announce = True
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
    month = event.get("month")
    try:
        draft = text(event.get("draft_text"), "draft_text", MAX_DRAFT_CHARS)
        if not isinstance(month, str) or len(month) != 7 or month[4] != "-":
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
        "actions_closed": _actions_closed(conn, client_id, month),
        "alerts_raised": _alerts_raised(conn, client_id, month),
        # No email addresses: these figures go into an AI prompt (automation 5).
    })


# --- reads for the automations ------------------------------------------------
# Ids, names, flags and work emails only: never order rows or customer references.

def _require(scope: dict, grant: str) -> None:
    if not scope.get(grant):
        raise Refused(403, f"this automation may not read {grant}")


def _active_client(conn, client_id) -> sqlite3.Row:
    client = conn.execute("SELECT * FROM clients WHERE id = ? AND is_active = 1",
                          (client_id,)).fetchone()
    if client is None:
        raise Refused(404, "unknown client")
    return client


def _month(value: str | None, default: str) -> str:
    month = value or default
    if len(month) != 7 or month[4] != "-" or not (month[:4] + month[5:]).isdigit():
        raise Refused(400, "month must look like 2026-10")
    return month


def _previous_month(day: date) -> str:
    return (day.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def _consultant_emails(conn, client_id: int) -> list[str]:
    return [r[0] for r in conn.execute(
        """SELECT u.email FROM users u
           JOIN client_assignments a ON a.user_id = u.id
           JOIN user_roles r ON r.user_id = u.id AND r.role = 'consultant'
           WHERE a.client_id = ? AND u.is_active = 1 AND u.is_service = 0
           ORDER BY u.email""", (client_id,))]


def _person(conn, user_id) -> dict | None:
    row = conn.execute("SELECT full_name, email FROM users WHERE id = ? AND is_active = 1",
                       (user_id,)).fetchone()
    return None if row is None else {"name": row["full_name"], "email": row["email"]}


def _actions_closed(conn, client_id: int, month: str) -> list[dict]:
    start, end = measure.month_range(month)
    rows = conn.execute(
        """SELECT a.id, a.title, a.decision, a.confidence, a.measured_benefit_eur
           FROM actions a WHERE a.client_id = ? AND a.status = 'closed'
             AND EXISTS (SELECT 1 FROM action_history h WHERE h.action_id = a.id
                         AND h.to_status = 'closed' AND substr(h.created_at, 1, 10) BETWEEN ? AND ?)
           ORDER BY a.id""", (client_id, start, end)).fetchall()
    return [dict(r) for r in rows]


def _alerts_raised(conn, client_id: int, month: str) -> list[str]:
    rows = conn.execute(
        """SELECT payload FROM automation_events
           WHERE client_id = ? AND event_type = 'alerts' AND status = 'accepted'
             AND substr(received_at, 1, 7) = ? ORDER BY id""", (client_id, month)).fetchall()
    return [json.loads(r["payload"]).get("message", "") for r in rows]


def business_days_between(start: date, end: date) -> int:
    """Weekdays after start, up to and including end."""
    days, day = 0, start
    while day < end:
        day += timedelta(days=1)
        days += day.weekday() < 5
    return days


MAX_CATCH_UP_DAYS = 31


@bp.route("/clients", methods=["GET"])
def clients():
    """The active clients, which month counts as 'last month' today, and for the
    intake, the next day of shop data each client needs and how many days behind
    yesterday it is (at most 31 per run, oldest first)."""
    authenticate()
    yesterday = today() - timedelta(days=1)
    out = []
    for row in get_db().execute(
            """SELECT c.id, c.name, (SELECT MAX(s.date) FROM sessions s WHERE s.client_id = c.id)
                      AS last_day FROM clients c WHERE c.is_active = 1 ORDER BY c.id"""):
        next_day = (date.fromisoformat(row["last_day"]) + timedelta(days=1)
                    if row["last_day"] else yesterday)
        behind = max(0, min((yesterday - next_day).days + 1, MAX_CATCH_UP_DAYS))
        out.append({"id": row["id"], "name": row["name"], "next_day": next_day.isoformat(),
                    "days_behind": behind})
    return jsonify({"clients": out, "today": today().isoformat(),
                    "last_month": _previous_month(today())})


@bp.route("/alerts", methods=["GET"])
def alerts():
    """What deserves an alert for one client. The app decides; Make only follows the flags.

    Below target: the growth system, or a running component, under the client's
    ROI target in the month (by default the latest month with results). Window
    ended: an approved action whose measurement period is over with no result.
    """
    _, scope = authenticate()
    _require(scope, "metrics")
    conn = get_db()
    client = _active_client(conn, request.args.get("client_id", type=int))
    latest = conn.execute("SELECT MAX(month) FROM component_months WHERE client_id = ?",
                          (client["id"],)).fetchone()[0]
    month = _month(request.args.get("month"), latest or _previous_month(today()))
    target, cid, flags = client["roi_target"], client["id"], []

    system = measure.system_month(conn, client, month)
    if system.roi is not None and system.roi < target:
        flags.append({"kind": "system_below_target", "item_id": cid,
                      "external_id": f"alert:{cid}:system:{month}", "path": f"/clients/{cid}",
                      "message": f"{client['name']}: growth-system ROI {system.roi:.0%} in {month} "
                                 f"is below the {target:.0%} target."})
    for row in measure.latest_component_months(conn, cid, month):
        cost = roi.component_month_cost(row["operating_cost_eur"], row["operating_hours"],
                                        client["hourly_rate_eur"])
        value = roi.continuation_roi(row["measured_benefit_eur"], cost)
        if value is not None and value < target:
            flags.append({"kind": "component_below_target", "item_id": row["component_id"],
                          "external_id": f"alert:{cid}:component:{row['component_id']}:{month}",
                          "path": f"/components/{row['component_id']}",
                          "message": f"{client['name']}: component '{row['name']}' returned "
                                     f"{value:.0%} in {month}, below the {target:.0%} target."})
    for action in conn.execute(
            """SELECT * FROM actions WHERE client_id = ? AND status = 'approved'
                 AND measured_benefit_eur IS NULL AND window_start IS NOT NULL
                 AND window_end IS NOT NULL ORDER BY id""", (cid,)):
        _, end = measure.measurement_period(action)
        if end < today().isoformat():
            flags.append({"kind": "window_ended", "item_id": action["id"],
                          "external_id": f"alert:{cid}:action:{action['id']}:window_ended",
                          "path": f"/actions/{action['id']}",
                          "message": f"{client['name']}: action #{action['id']} "
                                     f"'{action['title']}' finished measuring on {end} "
                                     f"and has no recorded result."})
    return jsonify({"client": {"id": cid, "name": client["name"]}, "month": month,
                    "flags": flags, "recipients": _consultant_emails(conn, cid)})


@bp.route("/actions/<int:action_id>", methods=["GET"])
def action_detail(action_id: int):
    """One action's routing facts: who asked, who reviews, where it stands."""
    _, scope = authenticate()
    _require(scope, "reviews")
    conn = get_db()
    action = conn.execute(
        """SELECT a.*, c.name AS client_name FROM actions a JOIN clients c ON c.id = a.client_id
           WHERE a.id = ?""", (action_id,)).fetchone()
    if action is None:
        raise Refused(404, "unknown action")
    last = conn.execute(
        """SELECT to_status, note, created_at FROM action_history WHERE action_id = ?
           ORDER BY id DESC LIMIT 1""", (action_id,)).fetchone()
    return jsonify({
        "id": action["id"], "title": action["title"], "status": action["status"],
        "client": {"id": action["client_id"], "name": action["client_name"]},
        "requester": _person(conn, action["requester_id"]),
        "reviewer": _person(conn, action["reviewer_id"]),
        "last_change": None if last is None else dict(last),
        "path": f"/actions/{action['id']}",
    })


@bp.route("/reviews", methods=["GET"])
def reviews():
    """Actions in review, with how many business days each has been waiting."""
    _, scope = authenticate()
    _require(scope, "reviews")
    minimum = request.args.get("min_business_days", default=0, type=int)
    if minimum < 0:
        raise Refused(400, "min_business_days must be 0 or more")
    conn, now, out = get_db(), today(), []
    for row in conn.execute(
            """SELECT a.id, a.title, a.client_id, a.reviewer_id, c.name AS client_name,
                      (SELECT MAX(h.created_at) FROM action_history h
                       WHERE h.action_id = a.id AND h.to_status = 'in_review') AS since
               FROM actions a JOIN clients c ON c.id = a.client_id
               WHERE a.status = 'in_review' ORDER BY a.id"""):
        since = date.fromisoformat(row["since"][:10]) if row["since"] else now
        waiting = business_days_between(since, now)
        if waiting >= minimum:
            out.append({"id": row["id"], "title": row["title"],
                        "client": {"id": row["client_id"], "name": row["client_name"]},
                        "reviewer": _person(conn, row["reviewer_id"]),
                        "business_days_waiting": waiting, "path": f"/actions/{row['id']}"})
    return jsonify({"actions": out})
