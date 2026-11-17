"""Sends the app's announcements (outbound_events) to Make.

An announcement is a doorbell, not a delivery: it carries ids only, and Make
reads what it needs back over the signed API. A row is marked delivered only
when Make's webhook accepts it; if Make cannot be reached, the row stays in the
outbox and goes out with the next send (after the next change, or with
`flask --app app send-announcements`).
"""

import hashlib
import hmac
import json
import sqlite3
import urllib.error
import urllib.request


def post_json(url: str, body: bytes, signature: str) -> bool:
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-Signature": signature})
    with urllib.request.urlopen(request, timeout=5) as response:
        return 200 <= response.status < 300


def dispatch(conn: sqlite3.Connection, webhooks: dict[str, str], secret: str,
             send=None, limit: int = 50) -> int:
    """Send undelivered announcements in order; return how many Make accepted."""
    send = send or post_json
    rows = conn.execute(
        "SELECT * FROM outbound_events WHERE delivered_at IS NULL ORDER BY id LIMIT ?",
        (limit,)).fetchall()
    delivered = 0
    for row in rows:
        url = webhooks.get(row["event_type"])
        if not url:
            continue                      # no scenario listens for this event yet
        body = json.dumps({"id": row["id"], "event_type": row["event_type"],
                           "client_id": row["client_id"], "entity_id": row["entity_id"]}).encode()
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest() if secret else ""
        try:
            accepted = send(url, body, signature)
        except (urllib.error.URLError, OSError):
            break                         # Make unreachable: keep the rest, in order, for later
        if not accepted:
            break
        conn.execute(
            """UPDATE outbound_events SET delivered_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE id = ? AND delivered_at IS NULL""", (row["id"],))
        conn.commit()
        delivered += 1
    return delivered
