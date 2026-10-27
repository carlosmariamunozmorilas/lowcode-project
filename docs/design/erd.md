# Data model — entity relationship diagram

Brief requirement 1: *at least 3 related tables, each with a primary key and the
foreign keys that link them.* MarketingOps has twelve. The DDL is
[`schema/001_initial.sql`](../../schema/001_initial.sql); field-level detail is in
[`specification.md` §3](../specification.md#3--entities).

```mermaid
erDiagram
    users ||--o{ requests : "raises (requester_id)"
    users |o--o{ requests : "owns (owner_id)"
    users |o--o{ requests : "is named reviewer of (reviewer_id)"
    projects ||--o{ requests : "contains"
    levers |o--o{ requests : "is pulled by"
    kpis ||--o{ levers : "is moved by"
    kpis |o--o{ kpis : "is parent of"
    requests ||--o{ request_transitions : "has history"
    users ||--o{ request_transitions : "acts in"
    requests ||--o{ tasks : "has"
    users |o--o{ tasks : "is assigned"
    requests ||--o{ review_checks : "is checked by"
    users |o--o{ review_checks : "passes"
    projects ||--o{ kpi_targets : "sets"
    kpis ||--o{ kpi_targets : "is targeted by"
    users ||--o{ kpi_targets : "sets (set_by)"
    kpi_targets |o--o| kpi_targets : "supersedes"
    projects ||--o{ kpi_measurements : "records"
    kpis ||--o{ kpi_measurements : "is measured by"
    users ||--o{ kpi_measurements : "records (recorded_by)"
    kpi_measurements |o--o| kpi_measurements : "supersedes"
    requests |o--o{ automation_events : "is opened by"
    requests |o--o{ outbound_events : "announces"

    users {
        int id PK
        text email "unique"
        text full_name
        text role "requester, owner, reviewer, admin, service"
        int is_active
    }
    projects {
        int id PK
        text name
        real budget_eur
        real roi_target
        real gross_margin
        real hourly_rate_eur
    }
    kpis {
        text key PK
        text name
        text unit
        text parent_key FK
    }
    levers {
        int id PK
        text key "unique"
        text name
        text kpi_key FK
    }
    requests {
        int id PK
        int project_id FK
        int requester_id FK
        int owner_id FK
        int reviewer_id FK
        int lever_id FK
        text status
        text hypothesis
        real expected_delta
        real cost_eur
        real cost_hours
        real actual_delta
        text confidence
    }
    request_transitions {
        int id PK
        int request_id FK
        int actor_id FK
        text from_status
        text to_status
        text note
        text created_at
    }
    tasks {
        int id PK
        int request_id FK
        int assignee_id FK
        text title
        int is_done
    }
    review_checks {
        int id PK
        int request_id FK
        int checked_by FK
        text check_key
        int passed
    }
    kpi_targets {
        int id PK
        int project_id FK
        text kpi_key FK
        int set_by FK
        int supersedes_id FK
        real baseline
        real target
    }
    kpi_measurements {
        int id PK
        int project_id FK
        text kpi_key FK
        int recorded_by FK
        int supersedes_id FK
        text period_week
        real value
        text source
    }
    automation_events {
        int id PK
        int request_id FK
        text source
        text external_id "unique with source"
        text payload
    }
    outbound_events {
        int id PK
        int request_id FK
        text event_type
        text payload
        text delivered_at
        int attempts
    }
```

## What the diagram is saying

**`requests` is the central table**, as `Ticket` is in the brief's helpdesk
example. It points at `users` three times — the person who asked, the
specialist who does the work and the reviewer named to sign it off — and the
rule that the reviewer is neither of the other two is enforced twice: by a
`CHECK` on the table and by `check_transition()` in `lifecycle.py`.

**Three tables only ever grow:** `request_transitions`, `kpi_targets` and
`kpi_measurements`. Database triggers abort any `UPDATE` or `DELETE`. A changed
target or a corrected figure is a new row whose `supersedes_id` points at the
one it replaces — the self-relationships in the diagram — so the history of
every number stays visible.

**`kpis` and `levers` are fixed reference data.** The KPI tree (gross profit ←
revenue ← sessions × conversion rate × average order value) is seeded by the
schema and never edited by users; each lever moves exactly one leaf KPI.

**Two tables belong to the automations.** `automation_events` is where the
automations' writes land, unique on `(source, external_id)` so a redelivery
changes nothing. `outbound_events` is the outbox: the events the application
announces to Make, written in the same transaction as the change they announce.

## The delete rule

The Week 5 sheet asks what happens to a project's tasks when the project is
deleted. Here nothing on the record is deleted: actions are cancelled, numbers
are superseded, users are deactivated or pseudonymised (see
[`gdpr.md`](gdpr.md)). Whether a whole project should be archivable is still an
open decision ❓ ([`specification.md` §10](../specification.md#10--open-questions-for-the-session-)).
