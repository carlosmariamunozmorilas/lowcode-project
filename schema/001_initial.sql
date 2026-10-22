-- Initial schema for MarketingOps with the ROI layer.
-- Drafted Week 2, reshaped 22 October for the ROI layer, finalised in Week 5
-- after the paper data model. The delete rule is still an open decision.

-- Marketing operations workflow — Week 5 schema (SQLite)
-- Dates stored as ISO 8601 text (YYYY-MM-DD HH:MM:SS), UTC.
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    email      TEXT    NOT NULL UNIQUE,
    full_name  TEXT    NOT NULL,
    role       TEXT    NOT NULL CHECK (role IN ('requester', 'owner', 'reviewer', 'admin')),
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- One store over one period. Margin and the hourly rate are project settings,
-- not levers: the ROI of every action in the project is computed with them.
CREATE TABLE projects (
    id              INTEGER PRIMARY KEY,
    name            TEXT    NOT NULL,
    period_start    TEXT    NOT NULL,
    period_end      TEXT    NOT NULL,
    budget_eur      REAL    NOT NULL CHECK (budget_eur >= 0),
    roi_target      REAL    NOT NULL,
    gross_margin    REAL    NOT NULL CHECK (gross_margin > 0 AND gross_margin <= 1),
    hourly_rate_eur REAL    NOT NULL CHECK (hourly_rate_eur >= 0),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (period_end > period_start)
);

-- The fixed KPI tree. Reference data, seeded below, never edited by users.
CREATE TABLE kpis (
    key        TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    unit       TEXT NOT NULL,
    parent_key TEXT REFERENCES kpis(key)
);

-- A lever moves exactly one leaf KPI. Reference data, seeded below.
CREATE TABLE levers (
    id      INTEGER PRIMARY KEY,
    key     TEXT    NOT NULL UNIQUE,
    name    TEXT    NOT NULL,
    kpi_key TEXT    NOT NULL REFERENCES kpis(key)
);

-- An action: a marketing request that names the lever it pulls and what it
-- costs, and is closed with the result it actually produced.
CREATE TABLE requests (
    id             INTEGER PRIMARY KEY,
    project_id     INTEGER NOT NULL REFERENCES projects(id),
    title          TEXT    NOT NULL,
    description    TEXT    NOT NULL DEFAULT '',
    request_type   TEXT    NOT NULL CHECK (request_type IN ('content', 'campaign', 'landing_page', 'data', 'lead', 'other')),
    status         TEXT    NOT NULL CHECK (status IN ('submitted', 'assigned', 'in_review', 'approved', 'closed', 'rejected', 'cancelled')),
    priority       TEXT    NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    requester_id   INTEGER NOT NULL REFERENCES users(id),
    owner_id       INTEGER          REFERENCES users(id),
    due_date       TEXT,
    lever_id       INTEGER          REFERENCES levers(id),
    hypothesis     TEXT    NOT NULL DEFAULT '',
    expected_delta REAL,
    cost_eur       REAL    NOT NULL DEFAULT 0 CHECK (cost_eur >= 0),
    cost_hours     REAL    NOT NULL DEFAULT 0 CHECK (cost_hours >= 0),
    window_start   TEXT,
    window_end     TEXT,
    actual_delta   REAL,
    confidence     TEXT             CHECK (confidence IN ('holdout', 'before_after', 'correlated')),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    -- An unowned request cannot be past the submitted stage.
    CHECK (status = 'submitted' OR status = 'cancelled' OR owner_id IS NOT NULL),
    -- Nothing is closed without its result and how sure we are of it.
    CHECK (status <> 'closed' OR (actual_delta IS NOT NULL AND confidence IS NOT NULL))
);

CREATE INDEX idx_requests_status  ON requests(status);
CREATE INDEX idx_requests_owner   ON requests(owner_id);
CREATE INDEX idx_requests_project ON requests(project_id);

-- Append-only. Every status change writes exactly one row. Never UPDATE or DELETE.
CREATE TABLE request_transitions (
    id          INTEGER PRIMARY KEY,
    request_id  INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status   TEXT    NOT NULL,
    actor_id    INTEGER NOT NULL REFERENCES users(id),
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_transitions_request ON request_transitions(request_id, created_at);

CREATE TRIGGER transitions_no_update BEFORE UPDATE ON request_transitions
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;

CREATE TRIGGER transitions_no_delete BEFORE DELETE ON request_transitions
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;

-- Append-only. A changed target is a new row pointing at the one it replaces,
-- so "who moved the target after the results came in" always has an answer.
CREATE TABLE kpi_targets (
    id            INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id),
    kpi_key       TEXT    NOT NULL REFERENCES kpis(key),
    baseline      REAL    NOT NULL,
    target        REAL    NOT NULL,
    set_by        INTEGER NOT NULL REFERENCES users(id),
    set_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    supersedes_id INTEGER          REFERENCES kpi_targets(id)
);

CREATE TRIGGER targets_no_update BEFORE UPDATE ON kpi_targets
BEGIN SELECT RAISE(ABORT, 'targets are append-only; add a row that supersedes'); END;

CREATE TRIGGER targets_no_delete BEFORE DELETE ON kpi_targets
BEGIN SELECT RAISE(ABORT, 'targets are append-only; add a row that supersedes'); END;

-- Append-only, one value per KPI per ISO week. A correction is a new row
-- pointing at the one it replaces; the latest row wins, the old one stays.
CREATE TABLE kpi_measurements (
    id            INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id),
    kpi_key       TEXT    NOT NULL REFERENCES kpis(key),
    period_week   TEXT    NOT NULL,
    value         REAL    NOT NULL,
    source        TEXT    NOT NULL CHECK (source IN ('manual', 'sheet_import')),
    recorded_by   INTEGER NOT NULL REFERENCES users(id),
    recorded_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    supersedes_id INTEGER          REFERENCES kpi_measurements(id)
);

CREATE INDEX idx_measurements_lookup ON kpi_measurements(project_id, kpi_key, period_week);

CREATE TRIGGER measurements_no_update BEFORE UPDATE ON kpi_measurements
BEGIN SELECT RAISE(ABORT, 'measurements are append-only; add a row that supersedes'); END;

CREATE TRIGGER measurements_no_delete BEFORE DELETE ON kpi_measurements
BEGIN SELECT RAISE(ABORT, 'measurements are append-only; add a row that supersedes'); END;

CREATE TABLE tasks (
    id           INTEGER PRIMARY KEY,
    request_id   INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    title        TEXT    NOT NULL,
    assignee_id  INTEGER          REFERENCES users(id),
    is_done      INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE review_checks (
    id         INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    check_key  TEXT    NOT NULL,
    passed     INTEGER NOT NULL DEFAULT 0,
    checked_by INTEGER          REFERENCES users(id),
    checked_at TEXT,
    UNIQUE (request_id, check_key)
);

-- Landing table for the automations that write. They POST here; they never
-- touch requests or measurements directly. external_id makes redelivery
-- idempotent.
CREATE TABLE automation_events (
    id          INTEGER PRIMARY KEY,
    source      TEXT    NOT NULL CHECK (source IN ('spend_revenue', 'performance', 'assistant')),
    external_id TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    request_id  INTEGER          REFERENCES requests(id),
    received_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source, external_id)
);

-- The fixed KPI tree and its levers.
INSERT INTO kpis (key, name, unit, parent_key) VALUES
    ('gross_profit',    'Gross profit',        'EUR',      NULL),
    ('revenue',         'Revenue',             'EUR',      'gross_profit'),
    ('sessions',        'Sessions',            'sessions', 'revenue'),
    ('conversion_rate', 'Conversion rate',     'ratio',    'revenue'),
    ('aov',             'Average order value', 'EUR',      'revenue');

INSERT INTO levers (key, name, kpi_key) VALUES
    ('paid_prospecting',   'Paid prospecting',         'sessions'),
    ('seo_content',        'SEO content',              'sessions'),
    ('email_traffic',      'Email traffic',            'sessions'),
    ('checkout_friction',  'Checkout friction',        'conversion_rate'),
    ('product_page',       'Product page',             'conversion_rate'),
    ('trust_signals',      'Trust signals',            'conversion_rate'),
    ('bundles',            'Bundles',                  'aov'),
    ('cross_sell',         'Cross-sell',               'aov'),
    ('free_shipping',      'Free-shipping threshold',  'aov');
