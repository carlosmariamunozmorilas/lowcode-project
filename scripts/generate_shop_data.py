"""Generate the fictional demo database (spec v2 §9).

Six months of shop data (May–October 2026) for three fictional stores, with a
fixed random seed so every run produces the same data, plus the agency team,
the plan templates, and a history of past actions whose effects are written
into the orders — so the dashboards have something to show on day one.

Honesty rule: the effects are put there by this script. The demo proves the
app measures correctly; it does not prove that any tactic works.

    python scripts/generate_shop_data.py [--database PATH]

Refuses to overwrite an existing file: nothing is ever deleted.
"""

import argparse
import math
import os
import random
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db  # noqa: E402
import measure  # noqa: E402

SEED = 20261102
START = date(2026, 5, 1)
END = date(2026, 10, 31)
TODAY = date(2026, 11, 2)
# Test accounts for the fictional team. Change DEMO_PASSWORD before any deploy.
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "fictional-demo-only")

SEASON = {5: 0.95, 6: 1.0, 7: 0.9, 8: 0.85, 9: 1.0, 10: 1.05}


@dataclass(frozen=True)
class Store:
    id: int
    code: str
    name: str
    sector: str
    products: str
    audience: str
    main_channels: str
    aov: float
    margin: float
    frequency: str
    budget: float
    roi_target: float
    business_model: str
    sessions_per_week: int
    conversion: float
    refund_rate: float
    returning_share: float
    shipping: float
    spread: float
    channels: dict[str, float]      # share of sessions and orders
    paid: dict[str, float]          # share of ad spend


STORES = (
    Store(1, "L", "Luna Home", "Homeware", "Decorative lighting, cushions, home accessories",
          "Home-decor buyers", "Meta, Google Shopping", 65.0, 0.35, "occasional", 5000.0, 0.20,
          "dtc", 12300, 0.018, 0.06, 0.25, 6.0, 0.35,
          {"meta": 0.30, "google_shopping": 0.25, "organic": 0.25, "email": 0.08, "direct": 0.12},
          {"meta": 0.55, "google_shopping": 0.45}),
    Store(2, "B", "Brote Cosmetics", "Skincare", "Natural skincare, with a subscription",
          "Eco-conscious skincare buyers", "Instagram, email", 30.0, 0.60, "monthly", 2000.0,
          0.20, "subscription", 4000, 0.025, 0.03, 0.45, 3.5, 0.30,
          {"instagram": 0.35, "email": 0.20, "organic": 0.25, "direct": 0.20},
          {"instagram": 1.0}),
    Store(3, "R", "Roble Muebles", "Furniture", "Furniture", "People furnishing a new home",
          "Google Search, Pinterest", 600.0, 0.25, "rare", 12000.0, 0.20, "dtc",
          6000, 0.006, 0.08, 0.02, 45.0, 0.40,
          {"google_search": 0.35, "pinterest": 0.20, "organic": 0.30, "direct": 0.15},
          {"google_search": 0.70, "pinterest": 0.30}),
)

PEOPLE = (
    # id, email, name, roles, clients
    (1, "ana.ruiz@agency.example", "Ana Ruiz", ("admin",), ()),
    (2, "marta.gil@agency.example", "Marta Gil", ("lead",), (1, 2, 3)),
    (3, "diego.sanz@agency.example", "Diego Sanz", ("lead",), (1, 2, 3)),
    (4, "lucia.vega@agency.example", "Lucía Vega", ("consultant",), (1, 2)),
    (5, "pablo.ortiz@agency.example", "Pablo Ortiz", ("consultant",), (1, 3)),
)
AUTOMATIONS = ((6, "shop_intake"), (7, "below_target_alert"), (8, "approval_routing"),
               (9, "report_draft"))


def days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def stamp(d: date, rng: random.Random | None = None) -> str:
    seconds = rng.randint(7 * 3600, 23 * 3600) if rng else 12 * 3600
    return f"{d.isoformat()}T{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}Z"


def poisson(rng: random.Random, lam: float) -> int:
    if lam < 30:
        limit, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rng.random()
            if p <= limit:
                return k
            k += 1
    return max(0, round(rng.gauss(lam, math.sqrt(lam))))


class ShopWriter:
    """Writes one store's orders, keeping its customers and counters."""

    def __init__(self, conn: sqlite3.Connection, store: Store, rng: random.Random):
        self.conn, self.s, self.rng = conn, store, rng
        self.customers: list[str] = []
        self.known: set[str] = set()
        self.next_customer = 1
        self.next_order = 1

    def new_ref(self) -> str:
        ref = f"C-{self.s.code}{self.next_customer:05d}"
        self.next_customer += 1
        return ref

    def pick_channel(self) -> str:
        r, acc = self.rng.random(), 0.0
        for channel, share in self.s.channels.items():
            acc += share
            if r <= acc:
                return channel
        return channel

    def order(self, day: date, customer: str | None = None, channel: str | None = None,
              extra_discount: float = 0.0, missing_cost: bool = False) -> int:
        s, rng = self.s, self.rng
        if customer is None:
            if self.customers and rng.random() < s.returning_share:
                customer = rng.choice(self.customers)
            else:
                customer = self.new_ref()
        is_new = customer not in self.known
        if is_new:
            self.known.add(customer)
            self.customers.append(customer)
        value = s.aov * math.exp(rng.gauss(-s.spread ** 2 / 2, s.spread))
        discount_share = 0.10 if rng.random() < 0.2 else 0.0
        discount_share += extra_discount
        gross = value
        net = round(gross * (1 - discount_share), 2)
        discount = round(gross - net, 2)
        shipping = round(s.shipping * rng.uniform(0.9, 1.1), 2)
        fee = round(net * 0.014 + 0.25, 2)
        product = round(max(gross * (1 - s.margin) - shipping - fee, gross * 0.15), 2)
        external = f"{s.code}-{self.next_order:06d}"
        self.next_order += 1
        cur = self.conn.execute(
            """INSERT INTO orders (client_id, external_id, ordered_at, customer_ref,
                   is_new_customer, channel, net_revenue_eur, discount_eur,
                   product_cost_eur, shipping_cost_eur, payment_fee_eur)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (s.id, external, stamp(day, rng), customer, int(is_new),
             channel or self.pick_channel(), net, discount,
             None if missing_cost else product, shipping, fee),
        )
        order_id = cur.lastrowid
        if rng.random() < s.refund_rate:
            refund_day = day + timedelta(days=rng.randint(3, 20))
            if refund_day <= TODAY - timedelta(days=1):
                self.conn.execute(
                    """INSERT INTO refunds (order_id, external_id, refunded_at, amount_eur,
                           restocked_cost_eur) VALUES (?, ?, ?, ?, ?)""",
                    (order_id, f"{external}-R", stamp(refund_day, rng), net,
                     round(product * 0.6, 2)),
                )
        return order_id


def daily_traffic(conn, w: ShopWriter, day: date, order_factor: float = 1.0,
                  extra_discount: float = 0.0) -> None:
    s, rng = w.s, w.rng
    weekday = 1.08 if day.weekday() >= 5 else 0.97
    base = s.sessions_per_week / 7 * SEASON[day.month] * weekday * rng.uniform(0.92, 1.08)
    for channel, share in s.channels.items():
        conn.execute("INSERT INTO sessions (client_id, date, channel, sessions) VALUES (?, ?, ?, ?)",
                     (s.id, day.isoformat(), channel, round(base * share)))
    daily_budget = s.budget * 12 / 365
    for channel, share in s.paid.items():
        conn.execute("INSERT INTO ad_spend (client_id, date, channel, spend_eur) VALUES (?, ?, ?, ?)",
                     (s.id, day.isoformat(), channel,
                      round(daily_budget * share * rng.uniform(0.9, 1.1), 2)))
    for _ in range(poisson(rng, base * s.conversion * order_factor)):
        w.order(day, extra_discount=extra_discount)


# --- people, clients, catalogue -------------------------------------------------

def seed_people(conn: sqlite3.Connection) -> None:
    from werkzeug.security import generate_password_hash

    hashed = generate_password_hash(DEMO_PASSWORD)  # Werkzeug scrypt
    for uid, email, name, roles, clients in PEOPLE:
        conn.execute("""INSERT INTO users (id, email, full_name, password_hash, created_at)
                        VALUES (?, ?, ?, ?, '2026-05-01T09:00:00Z')""", (uid, email, name, hashed))
        for role in roles:
            conn.execute("INSERT INTO user_roles (user_id, role) VALUES (?, ?)", (uid, role))
        for client in clients:
            conn.execute("INSERT INTO client_assignments (user_id, client_id) VALUES (?, ?)",
                         (uid, client))
    for uid, name in AUTOMATIONS:
        conn.execute(
            """INSERT INTO users (id, email, full_name, is_service, automation_name, created_at)
               VALUES (?, ?, ?, 1, ?, '2026-05-01T09:00:00Z')""",
            (uid, f"{name}@automation.example", f"Automation: {name.replace('_', ' ')}", name),
        )
        conn.execute("INSERT INTO user_roles (user_id, role) VALUES (?, 'service')", (uid,))


def seed_clients(conn: sqlite3.Connection) -> None:
    for s in STORES:
        conn.execute(
            """INSERT INTO clients (id, name, sector, products, audience, main_channels,
                   avg_order_value_eur, contribution_margin, purchase_frequency,
                   monthly_budget_eur, roi_target, hourly_rate_eur, business_model,
                   is_fictional, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 35, ?, 1, '2026-05-01T09:00:00Z')""",
            (s.id, s.name, s.sector, s.products, s.audience, s.main_channels, s.aov, s.margin,
             s.frequency, s.budget, s.roi_target, s.business_model),
        )


# --- past actions -----------------------------------------------------------------

def insert_action(conn, **fields) -> int:
    fields.setdefault("created_at", "2026-05-01T09:00:00Z")
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    return conn.execute(f"INSERT INTO actions ({cols}) VALUES ({marks})",
                        tuple(fields.values())).lastrowid


def history(conn, action_id: int, steps: list[tuple[str | None, str, int, str]]) -> None:
    for from_status, to_status, actor, when in steps:
        conn.execute(
            """INSERT INTO action_history (action_id, from_status, to_status, actor_id, note,
                   created_at) VALUES (?, ?, ?, ?, ?, ?)""",
            (action_id, from_status, to_status, actor, "seeded history", when),
        )


def standard_history(conn, action_id, requester, owner, reviewer, dates, final="closed"):
    path = [(None, "submitted", requester), ("submitted", "assigned", requester),
            ("assigned", "in_review", owner), ("in_review", "approved", reviewer),
            ("approved", "closed", reviewer)]
    stop = [s[1] for s in path].index(final) + 1
    history(conn, action_id, [(f, t, a, f"{d}T10:00:00Z")
                              for (f, t, a), d in zip(path[:stop], dates)])


def assign(conn, rng, action_id: int, refs: list[str], day: date, test_share: float) -> dict:
    groups = {}
    for ref in refs:
        g = "test" if rng.random() < test_share else "control"
        groups[ref] = g
        conn.execute("""INSERT INTO assignments (action_id, customer_ref, "group", assigned_at)
                        VALUES (?, ?, ?, ?)""", (action_id, ref, g, stamp(day)))
    return groups


def close_with_measurement(conn, action_id: int, decision: str, **extra) -> None:
    action = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    result = measure.action_measured_benefit(conn, action)
    benefit = extra.pop("measured_benefit_eur", None)
    confidence = extra.pop("confidence", None)
    if result is not None:
        benefit, confidence = result.benefit_eur, result.confidence
    conn.execute(
        """UPDATE actions SET status = 'closed', measured_benefit_eur = ?, confidence = ?,
               decision = ?, decision_note = ?, early_stop_reason = ?, evidence_note = ?
           WHERE id = ?""",
        (benefit, confidence, decision, extra.get("decision_note"),
         extra.get("early_stop_reason"), extra.get("evidence_note"), action_id),
    )


def generate(conn: sqlite3.Connection) -> None:
    rng = random.Random(SEED)
    db.load_plan_templates(conn)
    seed_clients(conn)
    seed_people(conn)
    writers = {s.id: ShopWriter(conn, s, rng) for s in STORES}
    luna, brote = writers[1], writers[2]

    # Luna Home, action 1: cart recovery, holdout — abandoners assigned 50/50 in
    # June, then 90/10 while the adopted flow keeps a small control group.
    cart = insert_action(
        conn, client_id=1, plan_template_id=65, discipline="automations",
        lifecycle_stage="conversion", title="Cart-abandonment email flow",
        hypothesis="If abandoned carts get a two-email reminder, then conversion of abandoners "
                   "will rise, because many abandon by distraction, without worsening margin or refunds",
        primary_metric="conversion", benefit_type="contribution", expected_benefit_eur=2500,
        setup_cost_eur=300, setup_hours=16, operating_cost_eur=120, operating_hours=6,
        hurdle_eur=500, comparison="holdout", window_start="2026-06-01", window_end="2026-06-28",
        post_period_days=14, requester_id=4, owner_id=5, reviewer_id=2, status="approved",
        benefit_key="luna:cart_recovery", created_at="2026-05-20T10:00:00Z")
    promo = insert_action(
        conn, client_id=1, plan_template_id=3, discipline="ecommerce",
        lifecycle_stage="conversion", title="Summer promotion: extra 15% off",
        hypothesis="If we add 15% off for two weeks, then orders will rise enough to raise "
                   "contribution, because summer demand is price-sensitive, without worsening "
                   "margin or refunds",
        primary_metric="orders", benefit_type="contribution", expected_benefit_eur=1200,
        setup_cost_eur=0, setup_hours=12, operating_cost_eur=800, operating_hours=8,
        hurdle_eur=500, comparison="before_after", window_start="2026-08-01",
        window_end="2026-08-14", post_period_days=14, requester_id=5, owner_id=5,
        reviewer_id=3, status="approved", benefit_key="luna:summer_promo",
        created_at="2026-07-20T10:00:00Z")
    agent = insert_action(
        conn, client_id=1, plan_template_id=50, discipline="agentic_ai",
        lifecycle_stage="operations", title="Read-only analytics agent replaces freelance report",
        hypothesis="If a read-only analytics agent drafts the monthly report, then the paid "
                   "freelance report can end, because the agent covers the same figures, "
                   "without worsening margin or refunds",
        primary_metric="avoided_cost", benefit_type="avoided_cost", expected_benefit_eur=1950,
        setup_cost_eur=0, setup_hours=20, operating_cost_eur=180, operating_hours=12,
        hurdle_eur=500, comparison="invoice", window_start="2026-07-01", window_end="2026-09-30",
        post_period_days=0, requester_id=5, owner_id=4, reviewer_id=3, status="approved",
        benefit_key="luna:reporting_cost", created_at="2026-06-20T10:00:00Z")
    reorder = insert_action(
        conn, client_id=1, plan_template_id=43, discipline="digital_growth",
        lifecycle_stage="repeat", title="Reorder-previous-basket shortcut",
        hypothesis="If past customers get a one-click reorder link, then repeat rate will rise, "
                   "because reordering is tedious, without worsening margin or refunds",
        primary_metric="repeat_rate", benefit_type="contribution", expected_benefit_eur=1500,
        setup_cost_eur=150, setup_hours=14, operating_cost_eur=0, operating_hours=4,
        hurdle_eur=500, comparison="holdout", window_start="2026-09-01", window_end="2026-09-28",
        post_period_days=152, requester_id=4, owner_id=5, reviewer_id=3, status="approved",
        benefit_key="luna:reorder", created_at="2026-08-20T10:00:00Z")

    # Brote Cosmetics: plan 20, email segmentation over its four groups, holdout.
    email = insert_action(
        conn, client_id=2, plan_template_id=20, discipline="digital_marketing",
        lifecycle_stage="retention", title="Email segmentation: four groups",
        hypothesis="If emails are segmented into lapsed, recent repeat, recent first-time and "
                   "prospects, then repeat purchases will rise, because each group gets a "
                   "relevant message, without worsening margin or refunds",
        primary_metric="repeat_rate", benefit_type="contribution", expected_benefit_eur=1200,
        setup_cost_eur=200, setup_hours=10, operating_cost_eur=0, operating_hours=4,
        hurdle_eur=500, comparison="holdout", window_start="2026-09-07", window_end="2026-09-20",
        post_period_days=0, requester_id=4, owner_id=4, reviewer_id=3, status="approved",
        benefit_key="brote:email_segments", created_at="2026-08-25T10:00:00Z")

    cart_groups: dict[str, str] = {}
    reorder_groups: dict[str, str] = {}
    email_groups: dict[str, str] = {}
    for day in days(START, END):
        for s in STORES:
            w = writers[s.id]
            factor, extra = 1.0, 0.0
            if s.id == 1 and date(2026, 8, 1) <= day <= date(2026, 8, 14):
                factor, extra = 1.22, 0.15          # the promotion
            elif s.id == 1 and date(2026, 8, 15) <= day <= date(2026, 8, 28):
                factor = 0.92                        # demand pulled forward
            daily_traffic(conn, w, day, factor, extra)
            if s.id == 2 and day == date(2026, 8, 14):
                w.order(day, missing_cost=True)      # one order arrives with no product cost

        # Cart abandoners at Luna: about 80 a day during the June pilot, then
        # about 40 a day reach the running flow.
        if day >= date(2026, 6, 1):
            pilot = day <= date(2026, 6, 28)
            if pilot or day >= date(2026, 7, 13):
                refs = [luna.new_ref() for _ in range(poisson(rng, 80 if pilot else 40))]
                groups = assign(conn, rng, cart, refs, day, 0.5 if pilot else 0.9)
                cart_groups.update(groups)
                for ref, g in groups.items():
                    if rng.random() < (0.16 if g == "test" else 0.05):
                        buy = day + timedelta(days=rng.randint(0, 6))
                        if buy <= END:
                            luna.order(buy, customer=ref, channel="email")

        if day == date(2026, 9, 1):
            past = sorted(luna.known)
            reorder_groups = assign(conn, rng, reorder, past, day, 0.5)
        if date(2026, 9, 1) <= day <= date(2026, 10, 15):
            for ref, g in reorder_groups.items():
                if g == "test" and rng.random() < 0.0006:
                    luna.order(day, customer=ref, channel="email")

        if day == date(2026, 9, 7):
            refs = sorted(brote.known) + [brote.new_ref() for _ in range(300)]  # + prospects
            email_groups = assign(conn, rng, email, refs, day, 0.5)
        if date(2026, 9, 7) <= day <= date(2026, 9, 20):
            for ref, g in email_groups.items():
                if g == "test" and rng.random() < 0.11 / 14:
                    brote.order(day, customer=ref, channel="email")

    # Close the past actions with the app's own measurement.
    close_with_measurement(
        conn, cart, "adopt",
        decision_note="Refund rate is compared with May, the first month of data, before "
                      "refunds had built up; June's rate matches the store's usual level, so "
                      "the breach is accepted.")
    standard_history(conn, cart, 4, 5, 2,
                     ["2026-05-20", "2026-05-21", "2026-05-25", "2026-05-27", "2026-07-14"])
    close_with_measurement(conn, promo, "reject",
                           decision_note="Contribution fell; the discount cost more than the "
                                         "extra orders brought in.")
    standard_history(conn, promo, 5, 5, 3,
                     ["2026-07-20", "2026-07-20", "2026-07-24", "2026-07-27", "2026-08-30"])
    close_with_measurement(
        conn, agent, "adopt", measured_benefit_eur=1950, confidence="documented",
        evidence_note="Freelance reporting invoices of €650 a month stopped from July "
                      "(contract ended 30 June); invoices for July–September are nil.",
        decision_note="Refund rate rose during the window, from damaged lamp shipments; "
                      "unrelated to reporting, so the breach does not argue against adopting.")
    standard_history(conn, agent, 5, 4, 3,
                     ["2026-06-20", "2026-06-21", "2026-06-24", "2026-06-26", "2026-10-02"])
    close_with_measurement(
        conn, reorder, "inconclusive", early_stop_reason="technical_failure",
        decision_note="The reorder link broke on mobile checkout; stopped before the "
                      "180-day horizon.")
    standard_history(conn, reorder, 4, 5, 3,
                     ["2026-08-20", "2026-08-21", "2026-08-25", "2026-08-27", "2026-10-20"])
    close_with_measurement(conn, email, "adopt")
    standard_history(conn, email, 4, 4, 3,
                     ["2026-08-25", "2026-08-26", "2026-08-31", "2026-09-02", "2026-10-05"])

    # Roble Muebles: a pilot still in progress.
    search = insert_action(
        conn, client_id=3, plan_template_id=30, discipline="performance_marketing",
        lifecycle_stage="acquisition", title="Search-term exclusions on furniture campaigns",
        hypothesis="If irrelevant search terms are excluded, then CPA will fall, because spend "
                   "stops going to queries that never buy, without worsening margin or refunds",
        primary_metric="cpa", benefit_type="contribution", expected_benefit_eur=3000,
        setup_cost_eur=0, setup_hours=32, operating_cost_eur=0, operating_hours=6,
        hurdle_eur=500, comparison="before_after", window_start="2026-10-01",
        window_end="2026-11-11", post_period_days=30, requester_id=5, owner_id=5, reviewer_id=2,
        status="approved", benefit_key="roble:search_terms", created_at="2026-09-20T10:00:00Z")
    standard_history(conn, search, 5, 5, 2,
                     ["2026-09-20", "2026-09-21", "2026-09-24", "2026-09-28"], final="approved")

    # Luna Home: one action waiting for Marta's review, one just proposed.
    waiting = insert_action(
        conn, client_id=1, plan_template_id=3, discipline="ecommerce",
        lifecycle_stage="conversion", title="Free-shipping threshold at €75",
        hypothesis="If free shipping starts at €75 instead of €60, then average order value "
                   "will rise, because shoppers add an item to qualify, without worsening "
                   "margin or refunds",
        primary_metric="average_order_value", benefit_type="contribution",
        expected_benefit_eur=1400, setup_cost_eur=0, setup_hours=6, operating_cost_eur=0,
        operating_hours=4, hurdle_eur=500, comparison="before_after", window_start="2026-11-09",
        window_end="2026-12-06", post_period_days=14, requester_id=5, owner_id=4,
        reviewer_id=2, status="in_review", benefit_key="luna:shipping_threshold",
        created_at="2026-10-28T10:00:00Z")
    standard_history(conn, waiting, 5, 4, 2, ["2026-10-28", "2026-10-29", "2026-10-31"],
                     final="in_review")
    proposed = insert_action(
        conn, client_id=1, plan_template_id=None, discipline="digital_growth",
        lifecycle_stage=None, title="Gift guide for the Christmas season",
        benefit_type="contribution", requester_id=4, status="submitted",
        created_at="2026-11-01T10:00:00Z")
    history(conn, proposed, [(None, "submitted", 4, "2026-11-01T10:00:00Z")])

    # The two components adopted at Luna Home.
    cart_component = conn.execute(
        """INSERT INTO components (client_id, origin_action_id, name, discipline, lifecycle_stage,
               benefit_type, measurement, status, started_on, benefit_key)
           VALUES (1, ?, 'Cart-abandonment email flow', 'automations', 'conversion',
                   'contribution', 'holdout_kept', 'running', '2026-07-13', 'luna:cart_recovery')""",
        (cart,)).lastrowid
    agent_component = conn.execute(
        """INSERT INTO components (client_id, origin_action_id, name, discipline, lifecycle_stage,
               benefit_type, measurement, status, started_on, benefit_key)
           VALUES (1, ?, 'Read-only analytics agent', 'agentic_ai', 'operations',
                   'avoided_cost', 'invoice', 'running', '2026-10-01', 'luna:reporting_cost')""",
        (agent,)).lastrowid
    component = conn.execute("SELECT * FROM components WHERE id = ?",
                             (cart_component,)).fetchone()
    for month in ("2026-07", "2026-08", "2026-09", "2026-10"):
        benefit, confidence = measure.component_benefit_for_month(conn, component, month)
        conn.execute(
            """INSERT INTO component_months (component_id, client_id, month, operating_cost_eur,
                   operating_hours, measured_benefit_eur, confidence, benefit_key, runs,
                   failed_runs, hours_freed, recorded_by, created_at)
               VALUES (?, 1, ?, 120, 6, ?, ?, 'luna:cart_recovery', ?, ?, 3, 5, ?)""",
            (cart_component, month, benefit, confidence, 30 + rng.randint(0, 1),
             rng.randint(0, 2), f"{measure.month_range(month)[1]}T18:00:00Z"))
    conn.execute(
        """INSERT INTO component_months (component_id, client_id, month, operating_cost_eur,
               operating_hours, measured_benefit_eur, confidence, benefit_key, runs, failed_runs,
               hours_freed, recorded_by, created_at)
           VALUES (?, 1, '2026-10', 60, 4, 650, 'documented', 'luna:reporting_cost', 4, 0, 10, 2,
                   '2026-10-31T18:00:00Z')""",
        (agent_component,))

    # Shop-data intake history: daily batches, one rejected for a total mismatch.
    for s in STORES:
        for day in days(date(2026, 10, 1), END):
            rejected = s.id == 1 and day == date(2026, 10, 17)
            conn.execute(
                """INSERT INTO automation_events (source, client_id, event_type, external_id,
                       payload, status, reason, received_at)
                   VALUES ('shop_intake', ?, 'shop_data', ?, '{}', ?, ?, ?)""",
                (s.id, f"{s.code}-{day.isoformat()}", "rejected" if rejected else "accepted",
                 "revenue total differs from control total by €12.40" if rejected else None,
                 f"{(day + timedelta(days=1)).isoformat()}T06:00:00Z"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", default=os.environ.get(
        "DATABASE_PATH", str(ROOT / "marketingops_v2.db")))
    args = parser.parse_args()
    path = Path(args.database)
    if path.exists():
        sys.exit(f"{path} already exists; nothing is deleted. Move it away first.")
    conn = db.connect(str(path), must_exist=False)
    db.create_schema(conn)
    with db.transaction(conn):
        generate(conn)
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("orders", "refunds", "assignments", "actions", "component_months")}
    conn.close()
    print(f"Demo database written to {path}: {counts}")


if __name__ == "__main__":
    main()
