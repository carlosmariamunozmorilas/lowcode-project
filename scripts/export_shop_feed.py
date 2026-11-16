"""Export the fictional stores' next days as a daily feed for automation 2.

The demo database ends on 31 October 2026. This script continues each store
from where the database stops (same customers, same order numbering) and
writes one row per store per day, as a store platform's daily export would:
the day's orders, refunds, sessions and ad spend as JSON, plus the export's own
control totals (row count and revenue). Automation 2 sends each row to
`POST /api/events` unchanged; the totals come from this source, never from Make.

November–January seasonality factors are illustrative settings for fictional
data, like the rest of the generator. Nothing is written to the database.

    python scripts/export_shop_feed.py --out feed.csv [--start 2026-11-01] [--end 2027-01-31]
"""

import argparse
import csv
import json
import random
import sqlite3
import sys
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import db  # noqa: E402
import generate_shop_data as gen  # noqa: E402

COLUMNS = ("date", "client_id", "client_code", "external_id", "expected_rows",
           "expected_revenue_eur", "orders_json", "refunds_json", "sessions_json",
           "ad_spend_json")
FEED_SEED = gen.SEED + 1
SEASON_EXTRA = {11: 1.15, 12: 1.25, 1: 0.85}     # illustrative: peak season, then January
MAX_CELL = 50_000                                 # Google Sheets' limit per cell


def continue_writer(conn, source, store, rng) -> gen.ShopWriter:
    """A writer that carries on a store from the source database."""
    writer = gen.ShopWriter(conn, store, rng)
    refs = [r[0] for r in source.execute(
        "SELECT customer_ref FROM orders WHERE client_id = ? ORDER BY id", (store.id,))]
    for ref in refs:
        if ref not in writer.known:
            writer.known.add(ref)
            writer.customers.append(ref)
    numbers = [int(r.split(store.code, 1)[1]) for r in writer.known if r.startswith(f"C-{store.code}")]
    writer.next_customer = max(numbers, default=0) + 1
    last = source.execute("SELECT MAX(external_id) FROM orders WHERE client_id = ?",
                          (store.id,)).fetchone()[0]
    writer.next_order = int(last.split("-")[-1]) + 1 if last else 1
    return writer


def build_feed(source: sqlite3.Connection, start: date, end: date) -> list[dict]:
    season, today = dict(gen.SEASON), gen.TODAY
    gen.SEASON.update(SEASON_EXTRA)
    gen.TODAY = end + timedelta(days=1)           # refunds up to the last exported day
    try:
        return _build(source, start, end)
    finally:
        gen.SEASON.clear()
        gen.SEASON.update(season)
        gen.TODAY = today


def _build(source: sqlite3.Connection, start: date, end: date) -> list[dict]:
    with tempfile.TemporaryDirectory() as folder:
        conn = db.connect(str(Path(folder) / "feed.db"), must_exist=False)
        db.create_schema(conn)
        gen.seed_clients(conn)
        rng = random.Random(FEED_SEED)
        writers = {s.id: continue_writer(conn, source, s, rng) for s in gen.STORES}
        for day in gen.days(start, end):
            for s in gen.STORES:
                gen.daily_traffic(conn, writers[s.id], day)
        rows = collect(conn, start, end)
        conn.close()
    return rows


def collect(conn, start: date, end: date) -> list[dict]:
    parts = defaultdict(lambda: {"orders": [], "refunds": [], "sessions": [], "ad_spend": []})
    for o in conn.execute("SELECT * FROM orders ORDER BY id"):
        parts[(o["ordered_at"][:10], o["client_id"])]["orders"].append({
            "external_id": o["external_id"], "ordered_at": o["ordered_at"],
            "customer_ref": o["customer_ref"], "is_new_customer": bool(o["is_new_customer"]),
            "channel": o["channel"], "net_revenue_eur": o["net_revenue_eur"],
            "discount_eur": o["discount_eur"], "product_cost_eur": o["product_cost_eur"],
            "shipping_cost_eur": o["shipping_cost_eur"], "payment_fee_eur": o["payment_fee_eur"]})
    for r in conn.execute("""SELECT r.*, o.external_id AS order_external_id, o.client_id
                             FROM refunds r JOIN orders o ON o.id = r.order_id ORDER BY r.id"""):
        parts[(r["refunded_at"][:10], r["client_id"])]["refunds"].append({
            "external_id": r["external_id"], "order_external_id": r["order_external_id"],
            "refunded_at": r["refunded_at"], "amount_eur": r["amount_eur"],
            "restocked_cost_eur": r["restocked_cost_eur"]})
    for s in conn.execute("SELECT * FROM sessions ORDER BY id"):
        parts[(s["date"], s["client_id"])]["sessions"].append(
            {"date": s["date"], "channel": s["channel"], "sessions": s["sessions"]})
    for a in conn.execute("SELECT * FROM ad_spend ORDER BY id"):
        parts[(a["date"], a["client_id"])]["ad_spend"].append(
            {"date": a["date"], "channel": a["channel"], "spend_eur": a["spend_eur"]})

    codes = {s.id: s.code for s in gen.STORES}
    out = []
    for day in gen.days(start, end):
        for s in gen.STORES:
            p = parts[(day.isoformat(), s.id)]
            row = {"date": day.isoformat(), "client_id": s.id, "client_code": codes[s.id],
                   "external_id": f"{codes[s.id]}-{day.isoformat()}",
                   "expected_rows": len(p["orders"]),
                   "expected_revenue_eur": round(sum(o["net_revenue_eur"] for o in p["orders"]), 2),
                   **{f"{k}_json": json.dumps(v, separators=(",", ":")) for k, v in p.items()}}
            too_big = [k for k in COLUMNS if len(str(row[k])) > MAX_CELL]
            if too_big:
                raise ValueError(f"{row['external_id']}: {too_big} exceed a Sheets cell")
            out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", default=str(ROOT / "marketingops_v2.db"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", default="2026-11-01")
    parser.add_argument("--end", default="2027-01-31")
    args = parser.parse_args()
    source = db.connect(args.database)
    rows = build_feed(source, date.fromisoformat(args.start), date.fromisoformat(args.end))
    source.close()
    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} store-days written to {args.out}")


if __name__ == "__main__":
    main()
