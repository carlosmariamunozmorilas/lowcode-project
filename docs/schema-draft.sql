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

CREATE TABLE requests (
    id            INTEGER PRIMARY KEY,
    title         TEXT    NOT NULL,
    description   TEXT    NOT NULL DEFAULT '',
    request_type  TEXT    NOT NULL CHECK (request_type IN ('content', 'campaign', 'landing_page', 'data', 'lead', 'other')),
    status        TEXT    NOT NULL CHECK (status IN ('submitted', 'assigned', 'in_review', 'approved', 'rejected', 'cancelled')),
    priority      TEXT    NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    requester_id  INTEGER NOT NULL REFERENCES users(id),
    owner_id      INTEGER          REFERENCES users(id),
    due_date      TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    -- An unowned request cannot be past the submitted stage.
    CHECK (status = 'submitted' OR status = 'cancelled' OR owner_id IS NOT NULL)
);

CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_owner  ON requests(owner_id);

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

-- Landing table for the three portfolio automations. They POST here; they never
-- touch requests directly. external_id makes redelivery idempotent.
CREATE TABLE automation_events (
    id          INTEGER PRIMARY KEY,
    source      TEXT    NOT NULL CHECK (source IN ('paid_media', 'performance', 'assistant')),
    external_id TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    request_id  INTEGER          REFERENCES requests(id),
    received_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source, external_id)
);
