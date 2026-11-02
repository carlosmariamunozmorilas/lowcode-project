-- MarketingOps v2 schema: a growth consultancy tool for online stores.
-- Specification: docs/specification-v2.md §3. Eighteen tables.
--
-- Nothing is ever deleted: every foreign key is ON DELETE RESTRICT, clients and
-- users are deactivated, actions are cancelled, and history and monthly records
-- are append-only (triggers below). Money is euros as REAL; dates are ISO 8601
-- text in UTC. Every connection must run PRAGMA foreign_keys = ON (db.py).

-- People and access ----------------------------------------------------------

CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    password_hash   TEXT,
    is_service      INTEGER NOT NULL DEFAULT 0 CHECK (is_service IN (0, 1)),
    automation_name TEXT UNIQUE,
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- A person always has a password hash; an automation never has one.
    CHECK ((is_service = 1 AND password_hash IS NULL)
        OR (is_service = 0 AND password_hash IS NOT NULL)),
    -- Each automation is one service user, named by automation_name.
    CHECK ((is_service = 1) = (automation_name IS NOT NULL))
);

CREATE TABLE user_roles (
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    role    TEXT NOT NULL CHECK (role IN ('consultant', 'lead', 'admin', 'service')),
    PRIMARY KEY (user_id, role)
);

CREATE TABLE clients (
    id                  INTEGER PRIMARY KEY,
    name                TEXT NOT NULL UNIQUE,
    sector              TEXT NOT NULL,
    products            TEXT NOT NULL,
    audience            TEXT NOT NULL,
    main_channels       TEXT NOT NULL,
    avg_order_value_eur REAL NOT NULL CHECK (avg_order_value_eur > 0),
    contribution_margin REAL NOT NULL CHECK (contribution_margin > 0 AND contribution_margin <= 1),
    purchase_frequency  TEXT NOT NULL CHECK (purchase_frequency IN ('rare', 'occasional', 'monthly')),
    monthly_budget_eur  REAL NOT NULL CHECK (monthly_budget_eur >= 0),
    roi_target          REAL NOT NULL,
    hourly_rate_eur     REAL NOT NULL DEFAULT 35 CHECK (hourly_rate_eur >= 0),
    business_model      TEXT NOT NULL CHECK (business_model IN
                            ('dtc', 'b2c', 'b2b', 'marketplace', 'subscription', 'omnichannel')),
    is_fictional        INTEGER NOT NULL DEFAULT 1 CHECK (is_fictional IN (0, 1)),
    is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE client_assignments (
    user_id   INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    client_id INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, client_id)
);

-- Catalogue ------------------------------------------------------------------

CREATE TABLE plan_templates (
    id                       INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND 72),
    discipline               TEXT NOT NULL CHECK (discipline IN
                                 ('ecommerce', 'digital_marketing', 'performance_marketing',
                                  'digital_growth', 'agentic_ai', 'automations')),
    title                    TEXT NOT NULL,
    summary                  TEXT NOT NULL,
    benefit_type             TEXT NOT NULL CHECK (benefit_type IN ('contribution', 'avoided_cost', 'enabler')),
    lifecycle_stage          TEXT NOT NULL,
    default_window_days      INTEGER NOT NULL CHECK (default_window_days > 0),
    default_post_period_days INTEGER NOT NULL CHECK (default_post_period_days >= 0),
    default_hurdle_eur       REAL NOT NULL CHECK (default_hurdle_eur >= 0),
    setup_hours              REAL NOT NULL CHECK (setup_hours >= 0),
    data_fit                 TEXT NOT NULL CHECK (data_fit IN ('yes', 'partial', 'no')),
    featured                 INTEGER NOT NULL DEFAULT 0 CHECK (featured IN (0, 1)),
    source_file              TEXT NOT NULL
);

-- One fact per row: what a plan moves, and which stores it suits.
CREATE TABLE plan_template_tags (
    plan_template_id INTEGER NOT NULL REFERENCES plan_templates (id) ON DELETE RESTRICT,
    kind             TEXT NOT NULL CHECK (kind IN ('moves', 'business_model', 'purchase_frequency')),
    value            TEXT NOT NULL,
    PRIMARY KEY (plan_template_id, kind, value)
);

-- The work -------------------------------------------------------------------

CREATE TABLE actions (
    id                   INTEGER PRIMARY KEY,
    client_id            INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    plan_template_id     INTEGER REFERENCES plan_templates (id) ON DELETE RESTRICT,
    discipline           TEXT NOT NULL CHECK (discipline IN
                             ('ecommerce', 'digital_marketing', 'performance_marketing',
                              'digital_growth', 'agentic_ai', 'automations')),
    lifecycle_stage      TEXT CHECK (lifecycle_stage IN
                             ('acquisition', 'activation', 'conversion', 'engagement', 'retention',
                              'repeat', 'expansion', 'referral', 'reactivation', 'operations')),
    title                TEXT NOT NULL,
    hypothesis           TEXT,
    primary_metric       TEXT CHECK (primary_metric IN
                             ('contribution', 'revenue', 'orders', 'sessions', 'conversion',
                              'average_order_value', 'new_customers', 'repeat_rate', 'cac', 'cpa',
                              'refund_rate', 'margin_pct', 'avoided_cost')),
    benefit_type         TEXT NOT NULL CHECK (benefit_type IN ('contribution', 'avoided_cost', 'enabler')),
    expected_benefit_eur REAL,
    setup_cost_eur       REAL NOT NULL DEFAULT 0 CHECK (setup_cost_eur >= 0),
    setup_hours          REAL NOT NULL DEFAULT 0 CHECK (setup_hours >= 0),
    operating_cost_eur   REAL NOT NULL DEFAULT 0 CHECK (operating_cost_eur >= 0),
    operating_hours      REAL NOT NULL DEFAULT 0 CHECK (operating_hours >= 0),
    hurdle_eur           REAL NOT NULL DEFAULT 500 CHECK (hurdle_eur >= 0),
    comparison           TEXT CHECK (comparison IN ('holdout', 'before_after', 'invoice', 'none')),
    window_start         TEXT,
    window_end           TEXT,
    post_period_days     INTEGER CHECK (post_period_days >= 0),
    requester_id         INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    owner_id             INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    reviewer_id          INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    status               TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN
                             ('submitted', 'assigned', 'in_review', 'approved', 'closed',
                              'rejected', 'cancelled')),
    measured_benefit_eur REAL,
    confidence           TEXT CHECK (confidence IN ('holdout', 'before_after', 'correlated', 'documented')),
    evidence_note        TEXT,
    decision             TEXT CHECK (decision IN ('adopt', 'revise', 'reject', 'inconclusive')),
    decision_note        TEXT,
    early_stop_reason    TEXT CHECK (early_stop_reason IN
                             ('data_quality_failure', 'technical_failure', 'customer_harm',
                              'financial_risk', 'legal_risk')),
    benefit_key          TEXT,
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- The reviewer is neither the requester nor the owner.
    CHECK (reviewer_id IS NULL OR (reviewer_id <> requester_id
                                   AND (owner_id IS NULL OR reviewer_id <> owner_id))),
    -- The comparison matches the benefit type.
    CHECK (comparison IS NULL
        OR (benefit_type = 'contribution' AND comparison IN ('holdout', 'before_after'))
        OR (benefit_type = 'avoided_cost' AND comparison = 'invoice')
        OR (benefit_type = 'enabler' AND comparison = 'none')),
    CHECK (window_start IS NULL OR window_end IS NULL OR window_end > window_start)
);

CREATE INDEX actions_client ON actions (client_id, status);

CREATE TABLE action_history (
    id          INTEGER PRIMARY KEY,
    action_id   INTEGER NOT NULL REFERENCES actions (id) ON DELETE RESTRICT,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    actor_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    note        TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TRIGGER action_history_no_update BEFORE UPDATE ON action_history
BEGIN SELECT RAISE(ABORT, 'action_history is append-only'); END;
CREATE TRIGGER action_history_no_delete BEFORE DELETE ON action_history
BEGIN SELECT RAISE(ABORT, 'action_history is append-only'); END;

-- Who is in a holdout's test or control group, buyers or not.
CREATE TABLE assignments (
    action_id    INTEGER NOT NULL REFERENCES actions (id) ON DELETE RESTRICT,
    customer_ref TEXT NOT NULL,
    "group"      TEXT NOT NULL CHECK ("group" IN ('test', 'control')),
    assigned_at  TEXT NOT NULL,
    UNIQUE (action_id, customer_ref)
);

CREATE TABLE components (
    id               INTEGER PRIMARY KEY,
    client_id        INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    origin_action_id INTEGER REFERENCES actions (id) ON DELETE RESTRICT,
    name             TEXT NOT NULL,
    discipline       TEXT NOT NULL,
    lifecycle_stage  TEXT NOT NULL,
    benefit_type     TEXT NOT NULL CHECK (benefit_type IN ('contribution', 'avoided_cost', 'enabler')),
    measurement      TEXT CHECK (measurement IN ('holdout_kept', 'pilot_estimate', 'invoice')),
    status           TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'review_due', 'retired')),
    started_on       TEXT NOT NULL,
    retired_on       TEXT,
    benefit_key      TEXT,
    CHECK ((benefit_type = 'enabler') = (measurement IS NULL))
);

CREATE TABLE component_months (
    id                   INTEGER PRIMARY KEY,
    component_id         INTEGER NOT NULL REFERENCES components (id) ON DELETE RESTRICT,
    client_id            INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    month                TEXT NOT NULL CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    operating_cost_eur   REAL NOT NULL DEFAULT 0 CHECK (operating_cost_eur >= 0),
    operating_hours      REAL NOT NULL DEFAULT 0 CHECK (operating_hours >= 0),
    measured_benefit_eur REAL,
    confidence           TEXT CHECK (confidence IN ('holdout', 'pilot_estimate', 'documented')),
    benefit_key          TEXT,
    runs                 INTEGER CHECK (runs >= 0),
    failed_runs          INTEGER CHECK (failed_runs >= 0),
    hours_freed          REAL CHECK (hours_freed >= 0),
    supersedes_id        INTEGER REFERENCES component_months (id) ON DELETE RESTRICT,
    recorded_by          INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Each benefit is counted once: one original benefit row per client, month and
-- key. Corrections (supersedes_id set) are checked in code.
CREATE UNIQUE INDEX component_months_benefit_once
    ON component_months (client_id, month, benefit_key)
    WHERE measured_benefit_eur IS NOT NULL AND supersedes_id IS NULL;

CREATE TRIGGER component_months_no_update BEFORE UPDATE ON component_months
BEGIN SELECT RAISE(ABORT, 'component_months is append-only'); END;
CREATE TRIGGER component_months_no_delete BEFORE DELETE ON component_months
BEGIN SELECT RAISE(ABORT, 'component_months is append-only'); END;

CREATE TABLE client_reports (
    id                  INTEGER PRIMARY KEY,
    client_id           INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    month               TEXT NOT NULL,
    draft_text          TEXT NOT NULL,
    final_text          TEXT,
    status              TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'rejected', 'sent')),
    was_corrected       INTEGER NOT NULL DEFAULT 0 CHECK (was_corrected IN (0, 1)),
    rejection_reason    TEXT,
    model               TEXT,
    prompt_version      TEXT,
    generation_cost_eur REAL CHECK (generation_cost_eur >= 0),
    reviewed_by         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    reviewed_at         TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (status <> 'rejected' OR rejection_reason IS NOT NULL),
    CHECK (status = 'draft' OR reviewed_by IS NOT NULL)
);

CREATE UNIQUE INDEX client_reports_one_live
    ON client_reports (client_id, month) WHERE status <> 'rejected';

-- Fictional shop data -------------------------------------------------------

CREATE TABLE orders (
    id                INTEGER PRIMARY KEY,
    client_id         INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    external_id       TEXT NOT NULL UNIQUE,
    ordered_at        TEXT NOT NULL,
    customer_ref      TEXT NOT NULL,
    is_new_customer   INTEGER NOT NULL CHECK (is_new_customer IN (0, 1)),
    channel           TEXT NOT NULL,
    net_revenue_eur   REAL NOT NULL CHECK (net_revenue_eur >= 0),
    discount_eur      REAL NOT NULL DEFAULT 0 CHECK (discount_eur >= 0),
    -- NULL means missing, never zero: dependent figures show as incomplete.
    product_cost_eur  REAL CHECK (product_cost_eur >= 0),
    shipping_cost_eur REAL CHECK (shipping_cost_eur >= 0),
    payment_fee_eur   REAL CHECK (payment_fee_eur >= 0)
);

CREATE INDEX orders_client_date ON orders (client_id, ordered_at);
CREATE INDEX orders_customer ON orders (client_id, customer_ref);

CREATE TABLE refunds (
    id                 INTEGER PRIMARY KEY,
    order_id           INTEGER NOT NULL REFERENCES orders (id) ON DELETE RESTRICT,
    external_id        TEXT NOT NULL UNIQUE,
    refunded_at        TEXT NOT NULL,
    amount_eur         REAL NOT NULL CHECK (amount_eur >= 0),
    restocked_cost_eur REAL NOT NULL DEFAULT 0 CHECK (restocked_cost_eur >= 0)
);

CREATE TABLE sessions (
    id        INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    date      TEXT NOT NULL,
    channel   TEXT NOT NULL,
    sessions  INTEGER NOT NULL CHECK (sessions >= 0),
    UNIQUE (client_id, date, channel)
);

CREATE TABLE ad_spend (
    id        INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    date      TEXT NOT NULL,
    channel   TEXT NOT NULL,
    spend_eur REAL NOT NULL CHECK (spend_eur >= 0),
    UNIQUE (client_id, date, channel)
);

-- Automations ----------------------------------------------------------------

CREATE TABLE automation_events (
    id                   INTEGER PRIMARY KEY,
    source               TEXT NOT NULL,
    client_id            INTEGER REFERENCES clients (id) ON DELETE RESTRICT,
    event_type           TEXT NOT NULL,
    external_id          TEXT NOT NULL,
    payload              TEXT NOT NULL,
    status               TEXT NOT NULL CHECK (status IN ('accepted', 'rejected', 'duplicate')),
    reason               TEXT,
    expected_rows        INTEGER,
    parsed_rows          INTEGER,
    expected_revenue_eur REAL,
    parsed_revenue_eur   REAL,
    received_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- A redelivered event changes nothing: one live row per source and external
-- id. Duplicates are still recorded, so the quality metrics can count them.
CREATE UNIQUE INDEX automation_events_once
    ON automation_events (source, external_id) WHERE status <> 'duplicate';

-- Ids-only announcements to Make, written in the same transaction as the
-- change they announce.
CREATE TABLE outbound_events (
    id           INTEGER PRIMARY KEY,
    event_type   TEXT NOT NULL,
    client_id    INTEGER REFERENCES clients (id) ON DELETE RESTRICT,
    entity_id    INTEGER,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    delivered_at TEXT
);
