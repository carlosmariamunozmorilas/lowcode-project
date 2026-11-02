"""Shared fixtures: a small, hand-made database, separate from the generated demo data."""

import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db  # noqa: E402
from app import create_app  # noqa: E402

PASSWORD = "fixture-password-only"
SECRETS = {"shop_intake": "intake-secret", "report_draft": "report-secret",
           "below_target_alert": "alert-secret"}

# Fixture people: ids are referred to by name in the tests.
ADMIN, LEAD_A, LEAD_B, CONSULTANT, OTHER_CONSULTANT = 1, 2, 3, 4, 5
INTAKE, REPORTER, ALERTER = 6, 7, 8
LUNA, OTHER = 1, 2


@pytest.fixture(scope="session")
def password_hash():
    return generate_password_hash(PASSWORD)


def build(conn, password_hash) -> None:
    db.create_schema(conn)
    db.load_plan_templates(conn)
    for cid, name in ((LUNA, "Luna Test"), (OTHER, "Other Store")):
        conn.execute(
            """INSERT INTO clients (id, name, sector, products, audience, main_channels,
                   avg_order_value_eur, contribution_margin, purchase_frequency,
                   monthly_budget_eur, roi_target, hourly_rate_eur, business_model)
               VALUES (?, ?, 'Homeware', 'Lamps', 'Buyers', 'Meta', 65, 0.35, 'occasional',
                       5000, 0.20, 35, 'dtc')""", (cid, name))
    people = ((ADMIN, "admin", ()), (LEAD_A, "lead", (LUNA,)), (LEAD_B, "lead", (LUNA, OTHER)),
              (CONSULTANT, "consultant", (LUNA,)), (OTHER_CONSULTANT, "consultant", (OTHER,)))
    for uid, role, clients in people:
        conn.execute("INSERT INTO users (id, email, full_name, password_hash) VALUES (?, ?, ?, ?)",
                     (uid, f"user{uid}@test.example", f"User {uid}", password_hash))
        conn.execute("INSERT INTO user_roles (user_id, role) VALUES (?, ?)", (uid, role))
        for c in clients:
            conn.execute("INSERT INTO client_assignments (user_id, client_id) VALUES (?, ?)",
                         (uid, c))
    for uid, name in ((INTAKE, "shop_intake"), (REPORTER, "report_draft"),
                      (ALERTER, "below_target_alert")):
        conn.execute(
            """INSERT INTO users (id, email, full_name, is_service, automation_name)
               VALUES (?, ?, ?, 1, ?)""", (uid, f"{name}@test.example", name, name))
        conn.execute("INSERT INTO user_roles (user_id, role) VALUES (?, 'service')", (uid,))
    conn.commit()


@pytest.fixture
def conn(tmp_path, password_hash):
    c = db.connect(str(tmp_path / "unit.db"), must_exist=False)
    build(c, password_hash)
    yield c
    c.close()


@pytest.fixture
def app(tmp_path, password_hash):
    path = tmp_path / "app.db"
    c = db.connect(str(path), must_exist=False)
    build(c, password_hash)
    c.close()
    return create_app({"DATABASE": str(path), "TESTING": True, "SECRET_KEY": "test",
                       "TODAY": "2026-11-02", "AUTOMATION_SECRETS": SECRETS})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def app_conn(app):
    c = db.connect(app.config["DATABASE"])
    yield c
    c.close()


def login(test_client, user_id: int) -> None:
    with test_client.session_transaction() as s:
        s["user_id"] = user_id
        s["csrf"] = "token"


def post(test_client, url: str, data: dict | None = None, **kwargs):
    return test_client.post(url, data={"csrf_token": "token", **(data or {})}, **kwargs)


def signed(test_client, url: str, body: dict, automation: str = "shop_intake",
           secret: str | None = None, method: str = "post"):
    raw = json.dumps(body).encode()
    key = (secret or SECRETS[automation]).encode()
    signature = hmac.new(key, raw, hashlib.sha256).hexdigest()
    return getattr(test_client, method)(
        url, data=raw, content_type="application/json",
        headers={"X-Automation": automation, "X-Signature": signature})


# --- data builders ---------------------------------------------------------------

_counter = {"order": 0}


def add_order(conn, day: str, customer: str, revenue: float = 100.0, product: float | None = 40.0,
              shipping: float | None = 5.0, fee: float | None = 2.0, discount: float = 0.0,
              client_id: int = LUNA, is_new: int = 0, channel: str = "meta") -> int:
    _counter["order"] += 1
    cur = conn.execute(
        """INSERT INTO orders (client_id, external_id, ordered_at, customer_ref, is_new_customer,
               channel, net_revenue_eur, discount_eur, product_cost_eur, shipping_cost_eur,
               payment_fee_eur) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, f"T-{_counter['order']}", f"{day}T12:00:00Z", customer, is_new, channel,
         revenue, discount, product, shipping, fee))
    return cur.lastrowid


def add_refund(conn, order_id: int, day: str, amount: float, restocked: float = 0.0) -> None:
    _counter["order"] += 1
    conn.execute(
        """INSERT INTO refunds (order_id, external_id, refunded_at, amount_eur, restocked_cost_eur)
           VALUES (?, ?, ?, ?, ?)""",
        (order_id, f"R-{_counter['order']}", f"{day}T12:00:00Z", amount, restocked))


def add_action(conn, **fields) -> int:
    base = dict(client_id=LUNA, discipline="ecommerce", title="Test action",
                benefit_type="contribution", requester_id=CONSULTANT, status="submitted")
    base.update(fields)
    cols = ", ".join(base)
    return conn.execute(f"INSERT INTO actions ({cols}) VALUES ({', '.join('?' for _ in base)})",
                        tuple(base.values())).lastrowid


def ready_action(conn, **fields) -> int:
    """An action complete enough to enter review."""
    base = dict(owner_id=CONSULTANT, reviewer_id=LEAD_A, hypothesis="If x then y",
                primary_metric="conversion", lifecycle_stage="conversion",
                expected_benefit_eur=1000, comparison="holdout", window_start="2026-06-01",
                window_end="2026-06-28", post_period_days=14, status="assigned")
    base.update(fields)
    return add_action(conn, **base)


def assign_customers(conn, action_id: int, test: list[str], control: list[str],
                     day: str = "2026-06-01") -> None:
    for group, refs in (("test", test), ("control", control)):
        for ref in refs:
            conn.execute(
                """INSERT INTO assignments (action_id, customer_ref, "group", assigned_at)
                   VALUES (?, ?, ?, ?)""", (action_id, ref, group, f"{day}T00:00:00Z"))
