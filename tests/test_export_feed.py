"""The daily feed for automation 2: one row per store per day, with its own totals."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import export_shop_feed  # noqa: E402


def test_feed_rows_carry_control_totals_that_match_their_orders(conn):
    rows = export_shop_feed.build_feed(conn, date(2026, 11, 1), date(2026, 11, 2))
    assert len(rows) == 6                                    # three stores, two days
    assert rows[0]["external_id"] == "L-2026-11-01"
    for row in rows:
        orders = json.loads(row["orders_json"])
        assert row["expected_rows"] == len(orders)
        assert row["expected_revenue_eur"] == round(sum(o["net_revenue_eur"] for o in orders), 2)
        assert all(o["ordered_at"].startswith(row["date"]) for o in orders)
