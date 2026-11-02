"""The fictional-data generator: spec v2 §11 test 22, and that its history obeys the app's rules."""

import importlib.util
from pathlib import Path

import pytest

import db
import lifecycle
import measure
import roi

ROOT = Path(__file__).resolve().parent.parent
SHOP_TABLES = ("orders", "refunds", "sessions", "ad_spend", "assignments")


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_shop_data", ROOT / "scripts" / "generate_shop_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    generator = load_generator()
    paths = []
    for name in ("one.db", "two.db"):
        path = tmp_path_factory.mktemp("gen") / name
        conn = db.connect(str(path), must_exist=False)
        db.create_schema(conn)
        with db.transaction(conn):
            generator.generate(conn)
        conn.close()
        paths.append(path)
    connections = [db.connect(str(p)) for p in paths]
    yield connections
    for c in connections:
        c.close()


def test_22_same_seed_same_data(demo):
    one, two = demo
    for table in SHOP_TABLES:
        rows_one = one.execute(f"SELECT * FROM {table} ORDER BY id" if table != "assignments"
                               else "SELECT * FROM assignments ORDER BY action_id, customer_ref").fetchall()
        rows_two = two.execute(f"SELECT * FROM {table} ORDER BY id" if table != "assignments"
                               else "SELECT * FROM assignments ORDER BY action_id, customer_ref").fetchall()
        assert [tuple(r) for r in rows_one] == [tuple(r) for r in rows_two], table
        assert rows_one, table


def test_every_client_is_fictional(demo):
    conn = demo[0]
    assert conn.execute("SELECT COUNT(*) FROM clients WHERE is_fictional = 0").fetchone()[0] == 0


def test_seeded_history_obeys_the_closing_rules(demo):
    """The demo must not break the app's own rules: every closed action could have
    been closed through lifecycle.check_close with the figures the app measures."""
    conn = demo[0]
    for row in conn.execute("""SELECT a.*, c.hourly_rate_eur FROM actions a
                               JOIN clients c ON c.id = a.client_id WHERE a.status = 'closed'"""):
        invested = roi.action_investment(row["setup_cost_eur"], row["setup_hours"],
                                         row["operating_cost_eur"], row["operating_hours"],
                                         row["hourly_rate_eur"])
        breached = any(g.breached for g in measure.window_guardrail_breach(
            conn, row["client_id"], row["window_start"], row["window_end"]))
        closed_on = conn.execute(
            """SELECT substr(created_at, 1, 10) FROM action_history
               WHERE action_id = ? AND to_status = 'closed'""", (row["id"],)).fetchone()[0]
        names = lifecycle.Action.__dataclass_fields__
        action = lifecycle.Action(**{k: row[k] for k in names if k in row.keys()})
        ctx = lifecycle.Context(
            today=__import__("datetime").date.fromisoformat(closed_on),
            net_benefit_eur=row["measured_benefit_eur"] - invested,
            guardrail_breached=breached)
        lifecycle.check_close(action, ctx)
