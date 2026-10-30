# Specification — MarketingOps, with the ROI layer

**Draft.** Written for Week 3 Block A, reshaped on 22 October for the ROI layer, aligned on 27 October with the *Low-Code/No-Code Project Brief* (a named reviewer, an outbox for event-triggered automations, a `service` role), then given rules drawn from my *ROI AI Influence Model* series (a prediction fixed before review, a decision at close, net gain and break-even, an AI cost line), to be refined in the live session on 28 October. Open questions are marked ❓ and are deliberately unresolved.

The brief's six minimum requirements — ERD, role table, data flow diagram, STRIDE, GDPR and the three automation types — are answered in [`design/`](design/README.md). What the 28 October lab generates first is a deliberately small slice: [`week03-slice.md`](week03-slice.md).

> **The pitch:** every piece of marketing work has to justify itself, and the record shows whether it did.

> **Version 2 (30 October 2026):** the product is now a growth consultancy tool for an agency serving several online stores, with fictional shop data and a growth-system dashboard per client — see [`product-definition-v2.md`](product-definition-v2.md). This specification remains the detailed reference for what v2 keeps (the action workflow, approval rules, ROI formulas, the append-only record); where the two disagree, v2 wins, and this document will be revised to match.

Companion documents: [`overview.md`](overview.md) explains the application in plain English; [`project-definition.md`](project-definition.md) covers the why, the scope boundaries and the weekly plan. This one is the technical surface.

---

## 1 · Stack

| Layer | Choice | Version | Arrives |
|---|---|---|---|
| Language | Python | 3.11+ | Week 1 |
| Back end | Flask | 3.1.0, pinned | Week 1 |
| Templating | Jinja2 | 3.1.6 (ships with Flask) | Week 3 |
| Data | SQLite | file-based | Week 5 |
| Data (prod) | PostgreSQL | 16, in Compose | Week 9 |
| CSS | Tailwind | via CDN | Week 6 |
| Charts | Chart.js | via CDN, no build step | Week 6 |
| Tests | pytest | | Week 7 |
| Lint | Ruff | with `ruff.toml` | Week 7 |
| Security | Bandit · Semgrep · pip-audit | | Week 8 |
| WSGI (prod) | Gunicorn | | Week 9 |
| Packaging | Docker, multi-stage, non-root | image < 250 MB | Week 9 |
| Hosting | AWS Lightsail container service | `linux/amd64`, `eu-west-1` | Week 10 |

No ORM. Raw SQL with parameterised queries — the Week 5 brief requires finding and removing string-formatted SQL, which is only meaningful if the SQL is visible.

**Known before the build:** Flask 3.1.0 and Werkzeug 3.1.3 carry six advisories between them (`pip-audit`, 21 October). The upgrade to Flask 3.1.3 and Werkzeug 3.1.9 happens when the Week 3 lab regenerates `requirements.txt`.

---

## 2 · Component list

```
lowcode-project/
├── app.py                    # application factory, config load, blueprint registration
├── config.py                 # settings from environment; no secrets in source
├── db.py                     # connection helper; PRAGMA foreign_keys=ON per connection; transactions
├── lifecycle.py              # ALLOWED transition map + check_transition()   ← core logic
├── roi.py                    # investment, incremental revenue and profit, ROI   ← core logic
├── auth.py                   # login, logout, session, @role_required decorator
│
├── models/
│   ├── users.py              # lookup, role checks
│   ├── projects.py           # create, read, settings
│   ├── requests.py           # actions: create, read, list, update status and results
│   ├── transitions.py        # append-only writes; timeline reads; metric aggregates
│   ├── targets.py            # append-only target versions; latest per KPI
│   ├── measurements.py       # append-only weekly values; latest per KPI and week
│   ├── tasks.py              # add, complete, count open per action
│   ├── checks.py             # mark passed, list required-by-type, all-passed test
│   ├── events.py             # automation_events insert with idempotency
│   └── outbound.py           # outbox writes; dispatcher posts pending announcements to Make, signed
│
├── routes/
│   ├── auth_routes.py        # /login, /logout
│   ├── project_routes.py     # /projects, targets, measurements
│   ├── request_routes.py     # action CRUD and the six lifecycle actions
│   ├── task_routes.py        # /requests/<id>/tasks, /tasks/<id>/complete
│   ├── check_routes.py       # /requests/<id>/checks/<key>
│   └── api_routes.py         # /api/events, /api/metrics
│
├── templates/
│   ├── base.html             # layout, nav, flash messages, landmarks
│   ├── login.html
│   ├── project_detail.html   # the KPI tree, KPIs against target, actions with ROI
│   ├── requests_list.html    # "my queue"
│   ├── request_new.html      # the action form
│   ├── request_detail.html   # detail + permitted actions + results + timeline
│   ├── _timeline.html        # partial: the transition history
│   └── _flash.html           # partial: status messages
│
├── static/app.css            # the little Tailwind cannot do
├── schema/001_initial.sql
├── tests/                    # see §6
├── security/                 # scan evidence, Week 8
└── docs/
```

Roughly twenty-five source files. That is "a real multi-file application" without being a framework.

**Why `lifecycle.py` and `roi.py` are separate modules with no Flask import:** they are pure functions over plain data, so Week 7 can test every transition rule and every formula without spinning up an app or a database. They are the two most testable things in the project and they should stay that way. Both already exist in the repository and run.

---

## 3 · Entities

### `users`

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `email` | TEXT | NOT NULL, UNIQUE |
| `full_name` | TEXT | NOT NULL |
| `password_hash` | TEXT | NOT NULL — Werkzeug scrypt hash, never the password (§10, question 6). *Not yet in `schema/001_initial.sql`; added when the schema is finalised.* |
| `role` | TEXT | NOT NULL, CHECK in (`requester`,`owner`,`reviewer`,`admin`,`service`) — `service` is one account per writing automation: no password, cannot sign in, never signs anything off. ⚠️ *Decided 28 October 2026 to allow **several roles per person**; this single column is the current design and is **not yet changed** — see "Multiple roles per user" below.* |
| `is_active` | INTEGER | NOT NULL DEFAULT 1 |
| `created_at` | TEXT | ISO 8601 UTC |

#### Multiple roles per user — decided, not yet built

**Decided 28 October 2026.** A person may hold more than one role, using the existing role names. What they may do is the union of their roles' permissions ([`design/roles.md`](design/roles.md)). The approval restriction is applied **by identity, not by role**: nobody may review, approve, reject or close an action they requested or own, whatever roles they hold, and `admin` never bypasses it. With no eligible reviewer, the action stays blocked. `service` stays an account type of its own, never combined with a human's roles, as in the current design.

**Implementation work this adds** (none of it exists yet; it is built with authentication):

- **Schema:** replace `users.role` with a `user_roles` table (`user_id`, `role`; primary key on both; the same CHECK on `role`), and migrate existing rows.
- **`lifecycle.py`:** `User.role: str` becomes `User.roles: frozenset[str]`, and the sign-off check asks whether the actor holds `reviewer` or `admin` rather than comparing one role. The identity checks (requester, owner, named reviewer) are already by user id and stay as they are.
- **Route authorisation:** every server-side permission check tests membership of the actor's roles; the interface shows the union of what those roles allow.
- **Tests:** tests 3–6, 15, 22 and 25–27 are restated for multi-role users, plus new cases — a person who is both requester and reviewer cannot review their own request; an `admin` who owns or requested an action cannot sign it off.
- **Seed:** one `user_roles` row per role a person holds (§8).

### `projects`

One store over one period, usually a quarter.

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | TEXT | NOT NULL |
| `period_start`, `period_end` | TEXT | NOT NULL, end after start |
| `budget_eur` | REAL | ≥ 0 |
| `roi_target` | REAL | e.g. 0.20, the Luna Home seed — €0.20 net per €1 invested |
| `gross_margin` | REAL | > 0 and ≤ 1 — a project setting, not a lever |
| `hourly_rate_eur` | REAL | ≥ 0 — the cost of an hour of people time |

### `kpis` and `levers` — fixed reference data

The KPI tree is not configurable. It is seeded by the schema and never edited by users.

```
gross_profit = revenue × gross_margin
└── revenue = sessions × conversion_rate × aov
    ├── sessions         ← levers: paid prospecting · SEO content · email traffic
    ├── conversion_rate  ← levers: checkout friction · product page · trust signals
    └── aov              ← levers: bundles · cross-sell · free-shipping threshold
```

`kpis`: `key` PK · `name` · `unit` · `parent_key` → `kpis`
`levers`: `id` PK · `key` UNIQUE · `name` · `kpi_key` → `kpis` — every lever moves exactly one leaf KPI.

### `requests` — the actions

A request is now an **action**: marketing work that names the lever it pulls and what it costs, and is closed with what it actually produced.

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `project_id` | INTEGER | FK → projects, NOT NULL |
| `title` | TEXT | NOT NULL |
| `description` | TEXT | NOT NULL DEFAULT '' |
| `request_type` | TEXT | CHECK in (`content`,`campaign`,`landing_page`,`data`,`lead`,`other`) — drives the review checks |
| `status` | TEXT | CHECK in (`submitted`,`assigned`,`in_review`,`approved`,`closed`,`rejected`,`cancelled`) |
| `priority` | TEXT | DEFAULT `normal`, CHECK in (`low`,`normal`,`high`) |
| `requester_id` | INTEGER | FK → users |
| `owner_id` | INTEGER | FK → users, nullable |
| `reviewer_id` | INTEGER | FK → users, nullable — named by the owner when sending to review; must have role `reviewer` or `admin` (checked by the route) and be neither requester nor owner (checked by the table) |
| `due_date` | TEXT | nullable |
| `lever_id` | INTEGER | FK → levers — required before review |
| `hypothesis` | TEXT | required before review — *"removing forced sign-up lifts conversion by 0.3 points"* |
| `expected_delta` | REAL | in the lever's KPI unit — sessions +8000 · conversion +0.003 · AOV +3.00 — **required before review**, so the prediction is fixed before any result exists |
| `cost_eur` | REAL | cash, ≥ 0, default 0 |
| `cost_hours` | REAL | people time, ≥ 0, default 0 |
| `window_start`, `window_end` | TEXT | the measurement window — **required before review**, end after start |
| `actual_delta` | REAL | required to close |
| `confidence` | TEXT | required to close, CHECK in (`holdout`,`before_after`,`correlated`) |
| `decision` | TEXT | required to close, CHECK in (`scale`,`hold`,`redesign`,`retire`) — what the team does next with what it learned |
| `ai_assisted` | INTEGER | 0 or 1 — was AI used to do the work? **Planned for Weeks 5–6, not yet in the schema** |
| `ai_cost_eur` | REAL | ≥ 0, default 0 — AI tools and usage for this action, counted in its investment. **Planned for Weeks 5–6** |
| `created_at` | TEXT | |

Table-level CHECKs: a request may only be `submitted` or `cancelled` while `owner_id IS NULL`; from `in_review` on it must have a `reviewer_id`, who is neither its requester nor its owner, and its `expected_delta` and measurement window; a request may only be `closed` with `actual_delta`, `confidence` and `decision` set.

### `request_transitions` — the heart

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `request_id` | INTEGER | FK → requests ON DELETE CASCADE |
| `from_status` | TEXT | nullable (first row) |
| `to_status` | TEXT | NOT NULL |
| `actor_id` | INTEGER | FK → users |
| `note` | TEXT | DEFAULT '' |
| `created_at` | TEXT | |

Two triggers abort `UPDATE` and `DELETE`. Index on `(request_id, created_at)`.

### `kpi_targets` and `kpi_measurements` — append-only numbers

`kpi_targets`: `id` · `project_id` FK · `kpi_key` FK · `baseline` · `target` · `set_by` FK · `set_at` · `supersedes_id` FK nullable
`kpi_measurements`: `id` · `project_id` FK · `kpi_key` FK · `period_week` (ISO week, e.g. `2026-W44`) · `value` · `source` CHECK in (`manual`,`sheet_import`) · `recorded_by` FK · `recorded_at` · `supersedes_id` FK nullable

Both behave like `request_transitions`: triggers abort `UPDATE` and `DELETE`. A changed target or a corrected measurement is a **new row that points at the one it replaces**. The current value is the latest row not superseded by another; the old one stays. *"Who moved the target after the results came in"* always has an answer.

### `tasks`

`id` · `request_id` FK · `title` · `assignee_id` FK nullable · `is_done` INTEGER · `created_at` · `completed_at` nullable

### `review_checks`

`id` · `request_id` FK · `check_key` TEXT · `passed` INTEGER · `checked_by` FK nullable · `checked_at` nullable · UNIQUE `(request_id, check_key)`

Check keys, taken from the governance layer of the AI-Era influence model rather than invented:

| `check_key` | Applies to | Asks |
|---|---|---|
| `claims_evidenced` | all | Is every claim backed by approved evidence? |
| `brand_and_disclosure` | all | Brand consistent, rights cleared, disclosure present? |
| `data_use_permitted` | campaign, data, lead | Is this data use and retention permitted? |
| `audience_eligible` | campaign | Audience eligibility, exclusions, sensitive targeting checked? |
| `links_resolve` | content, landing_page | Does every link return 200? |
| `tracking_present` | campaign, landing_page | UTMs and conversion tag in place? |
| `accessible` | landing_page | Contrast, labels, keyboard navigation — reuses Week 6 |

### `automation_events`

`id` · `source` CHECK in (`spend_revenue`,`performance`,`assistant`) · `external_id` TEXT · `payload` TEXT (JSON) · `request_id` FK nullable · `received_at` · **UNIQUE `(source, external_id)`**

### `outbound_events` — the outbox

`id` · `event_type` CHECK in (`measurement.recorded`,`action.in_review`,`action.decided`) · `request_id` FK nullable · `payload` TEXT (JSON, **ids only**) · `created_at` · `delivered_at` nullable · `attempts`

Written in the same transaction as the change it announces. Not part of the record: the delivery columns are updated, and delivered rows are deleted after 90 days ❓ ([`design/gdpr.md`](design/gdpr.md)).

---

## 4 · Routes

| Method | Path | Who | Does |
|---|---|---|---|
| GET/POST | `/login` | anyone | session start |
| POST | `/logout` | signed in | session end |
| GET | `/projects` | signed in | list |
| POST | `/projects` | admin | create |
| GET | `/projects/<id>` | signed in | the KPI tree, KPIs against target, actions with expected and realised ROI, the project's planned ROI |
| POST | `/projects/<id>/targets` | admin | a new target version — never an edit |
| POST | `/projects/<id>/measurements` | owner, admin | a weekly measurement or a correction — never an edit |
| GET | `/requests` | signed in | my queue: owned actions + assigned tasks, by due date |
| GET | `/requests/new` | signed in | the form |
| POST | `/requests/preview` | signed in | re-renders the form with its **before-action preview** — the action's own ROI, net gain and break-even, the project's planned ROI without and with it, and the lever's track record. **Writes nothing** |
| POST | `/requests` | signed in | create → `submitted`, writes transition #1 |
| GET | `/requests/<id>` | signed in | detail, permitted actions, expected and actual results, timeline |
| POST | `/requests/<id>/assign` | owner, admin | set `owner_id` → `assigned` |
| POST | `/requests/<id>/review` | owner, admin | → `in_review` with a named `reviewer_id`, **refused if open tasks, no lever and hypothesis, no expected change and window, or no eligible reviewer**; announces `action.in_review` |
| POST | `/requests/<id>/approve` | named reviewer | → `approved`, **refused unless the actor is the reviewer named on this action, or if checks unpassed**; announces `action.decided` |
| POST | `/requests/<id>/reject` | named reviewer | → `rejected`; announces `action.decided` |
| POST | `/requests/<id>/close` | named reviewer | → `closed` with `actual_delta`, `confidence` and `decision`, **refused unless the named reviewer** |
| POST | `/requests/<id>/cancel` | requester, admin | → `cancelled` |
| POST | `/requests/<id>/tasks` | owner, admin | add task |
| POST | `/tasks/<id>/complete` | assignee, owner, admin | mark done |
| POST | `/requests/<id>/checks/<key>` | reviewer, admin | mark check passed |
| POST | `/api/events` | HMAC signature | automation intake, idempotent |
| GET | `/api/metrics` | HMAC signature | aggregates: KPIs against target with an `off_target` flag the app computes, ROI, cycle times; with `awaiting_review`, the actions in review, their named reviewer's email and days waiting |

Every lifecycle route goes through `check_transition()` before writing. No route writes a status directly.

**Every status change is one transaction.** The route updates `requests.status` and inserts the matching `request_transitions` row inside a single database transaction: both are written, or neither is. Without that, a failure between the two writes leaves a request whose status says one thing and whose history says another — an approval with no record of who approved it, which is the one thing this application exists to prevent. Test 10 checks the result; the transaction is what guarantees it. Closing writes `actual_delta`, `confidence` and the transition in the same transaction. A change that is announced to Make writes its `outbound_events` row in that same transaction too (test 29).

**Mass assignment.** Status, `actual_delta` and `confidence` are never read from a general edit form. They change only through the lifecycle routes, which check who is acting.

### `POST /api/events`

```json
{ "source": "spend_revenue", "external_id": "sessions:2026-W44:3f9a1c", "payload": { } }
```

Header `X-Signature`: HMAC-SHA256 of the raw body with a shared secret from the environment.

| Case | Response |
|---|---|
| Valid, new | `201` + the id of what it created |
| Valid, already seen | `200`, no-op |
| Bad signature | `401` |
| Malformed / missing fields | `400` — never a 500 |

| `source` | Creates |
|---|---|
| `spend_revenue` | a `kpi_measurements` row, `source = 'sheet_import'`; if that KPI already has a value for that week, the new row supersedes it |
| `performance` | an action for the drifting KPI — or, if one is already open for that KPI, a task on it |

For `spend_revenue`, `external_id` is `"{kpi}:{iso_week}:{short hash of the value}"`. The same value delivered twice is a no-op; a **corrected** value has a different hash, so it is recorded as a correction instead of being ignored ❓.

### Outbound announcements — the application's only outward call

Three events, each written to `outbound_events` in the transaction that causes it:

| Event | Written when | Payload | Drives |
|---|---|---|---|
| `measurement.recorded` | a measurement or correction is recorded, by hand or by automation 1 | `project_id`, `kpi_key`, `period_week`, `measurement_id` | automation 2, drift alert |
| `action.in_review` | an action enters review | `request_id`, `reviewer_id` | automation 3, approval routing |
| `action.decided` | an action is approved or rejected | `request_id`, `decision` | automation 3, approval routing |

After the commit, the dispatcher posts every undelivered row, oldest first, to `MAKE_WEBHOOK_URL` with an `X-Signature` HMAC header. A `2xx` sets `delivered_at`; anything else increments `attempts` and leaves the row for the next delivery. `flask deliver-events` retries by hand.

**Ids only, never content** — no title, hypothesis, figure or name (test 30). Make reads what it needs back through the signed `GET /api/metrics`. So a forged announcement achieves nothing but a read of the true state, and no action content sits in Make's execution history ([`design/stride.md`](design/stride.md), T11–T12).

---

## 5 · Templates

| Template | Shows |
|---|---|
| `base.html` | nav, flash region, skip link, landmarks |
| `login.html` | email + password, labelled inputs |
| `project_detail.html` | the KPI tree; each KPI against target, as text *and* a chart; actions with expected and realised ROI; planned and realised project ROI against `roi_target`; each lever's track record |
| `requests_list.html` | my queue; status as text *and* colour, never colour alone |
| `request_new.html` | title, type, priority, due date, description, lever, hypothesis, expected change, cost in euros and hours, measurement window; a **Preview** button and, once pressed, the before-action panel (below) |
| `request_detail.html` | fields; expected ROI, net gain and **break-even revenue** — *"this action must add €X of revenue to break even"*; the named reviewer; once closed, actual result, confidence, decision and realised ROI; the action buttons the viewer is actually allowed; tasks; checks. Sending to review asks the owner to pick a reviewer from the eligible ones |
| `_timeline.html` | every transition: who, from, to, when, note |
| `_flash.html` | success and error messages |

**ROI is shown with its basis.** Every ROI figure on screen says whether it is expected or realised and, if realised, its confidence label. A `correlated` result is never displayed as if it were proven. Next to every ratio sits the net gain in euros, so a loss reads as a loss and an action with no investment — no ROI — still shows what it returned.

**Week 8 trap to avoid:** `request_detail.html` hides buttons the viewer may not use. Hiding a button is not authorisation. Every route re-checks server-side, and there will be tests that curl `/approve` and `/close` as the requester and expect a refusal.

---

## 6 · Tests

Week 7 asks for at least eight covering valid, invalid, empty and boundary input.

**`test_lifecycle.py`** — no app, no database
1. Every legal transition is allowed
2. Every illegal transition is refused (`submitted → approved`, `in_review → closed` etc.)
3. A requester cannot approve their own request
4. The owner cannot approve work they did
5. A wrong role cannot approve
6. An independent reviewer can
7. `assigned → assigned` is legal and still records a transition

**`test_requests.py`**
8. A request with an open task cannot enter review
9. A request with unpassed required checks cannot be approved
10. `requests.status` always equals the latest transition's `to_status` — including when the transition insert fails, in which case the status change is rolled back too

**`test_api_events.py`**
11. A valid signed `spend_revenue` event records a measurement
12. The same `external_id` twice records one measurement, not two
13. A bad signature returns 401
14. An empty body, a missing field and a 10,000-character name each return 400, not 500

**`test_auth.py`**
15. `POST /requests/<id>/approve` by the requester returns 403 even though the button is hidden

**`test_roi.py`** — no app, no database
16. The worked example's action A returns ROI 3.29
17. An action with ROAS above 1 can have negative ROI: action B, ROAS 1.92, ROI −0.28
18. People time counts: no cash and 24 hours at €35 is an investment of €840, not zero
19. Zero investment returns `None`, not a division error
20. Lower margin, same revenue, lower ROI

**`test_close.py`**
21. Closing is refused without `actual_delta`, and without a valid confidence label
22. The owner cannot close their own action
23. A corrected measurement does not overwrite: the old row stays, the latest wins

**`test_lifecycle.py`, continued — the named reviewer** (added 27 October for the brief)
24. An action cannot enter review without a named reviewer
25. The named reviewer cannot be the requester or the owner
26. A reviewer who is not the one named on the action cannot approve, reject or close it — the forwarded-link case
27. The named reviewer can approve, and later close
28. A `service` account cannot approve or close anything

**`test_outbound.py`**
29. Sending an action to review writes its status, its transition and its `action.in_review` announcement together — and if the announcement insert fails, none of the three is written
30. An announcement payload contains ids only — no title, hypothesis, figure, name or email

**`test_roi.py` and `test_lifecycle.py`, continued — fixed predictions and decisions**
31. Net gain and break-even revenue for the worked example: B must add €13,375 of revenue to break even, against the €9,600 it was expected to bring
32. A loss is reported as computed: €500 of lost profit on €200 invested is an ROI of −3.5, never clipped to −1 or to zero
33. An action cannot enter review without its expected change and a measurement window that ends after it starts
34. An action cannot be closed without a decision
35. A decision outside `scale`, `hold`, `redesign`, `retire` is refused

**`test_roi.py`, continued — the before-action preview**
36. Proposing D in the worked example moves the project's planned ROI from 0.19 to 0.18: an action with its own positive ROI (0.13) lowers the project's, because it earns less per euro than the project already does
37. A track record divides totals, not ratios: expected 0.003 and 0.002, actual 0.003 and 0.0005, is a realisation of 0.70 — not the 0.63 an average of the two ratios would give
38. A lever with no closed actions, or whose expected changes sum to zero, has no realisation (`None`), not zero
39. The preview route writes nothing: after `POST /requests/preview` the requests, transitions and outbound tables are unchanged

Thirty-nine. Deliberately more than eight, and 1–7, 16–20, 24–28 and 31–38 run in milliseconds. The AI fields (§3) bring their own tests when they are built.

### The worked example — the numbers the tests use

**A test fixture, independent of the seed data.** This example has its own store, a 40% margin and its own actions A, B, C and D; the tests above depend on these exact figures, so they do not change. It is **not** the Luna Home scenario that seeds the demo (§8), and the two sets of numbers are not meant to match.

Baseline for one 30-day window: 50,000 sessions · 2.0% conversion · €60 AOV = €60,000 revenue. Margin 40%. People time €35/hour.

| Action | Lever → KPI | Expected change | Revenue | Gross profit | Investment | Net gain | Break-even revenue | ROI | ROAS |
|---|---|---|---|---|---|---|---|---|---|
| A · Remove forced sign-up | checkout friction → conversion | +0.3 points | €9,000 | €3,600 | €840 (24 h) | €2,760 | €2,100 | **3.29** | n/a |
| B · Meta prospecting | paid prospecting → sessions | +8,000 | €9,600 | €3,840 | €5,350 (€5,000 + 10 h) | −€1,510 | €13,375 | **−0.28** | 1.92 |
| C · Two bundles | bundles → AOV | +€3.00 | €3,000 | €1,200 | €1,080 (€800 + 8 h) | €120 | €2,700 | **0.11** | 3.75 |
| **Project** | | | €21,600 | €8,640 | €7,270 | €1,370 | | **0.19** | |

Already verified against `roi.py`. B looks healthy on ROAS and loses money; A costs no cash and returns the most. That contrast is the argument of the whole application. Break-even makes it visible before anything is spent: B needs €13,375 of extra revenue to cover its cost, and its own hypothesis only claims €9,600.

**ROI divides by the full investment of the action** — cash plus people time, and from Weeks 5–6 its AI cost. The same gain over a different denominator gives a different ratio, so the denominator is stated wherever ROI is.

### What the app never counts

Stated so nobody, human or generated code, quietly adds them back:

- **Saved hours as a benefit.** Time is counted as a cost. Hours an action "frees up" become money only when spending actually falls, and the app has no way to know that.
- **ROAS or platform-attributed revenue as a result.** Only the measured change in the store's own KPIs is a result.
- **ROI percentages added together.** A project's ROI is total profit change against total investment, never a sum or average of the actions' ratios.
- **A result as more certain than it is.** Every realised figure carries its confidence label.

### The before-action preview

Anyone signed in can fill in the action form and press **Preview** — before saving anything, before any approval — and see what the action would mean:

> **D · Free-shipping threshold** — free-shipping lever → AOV +€2.00, €500 + 6 hours
> Its own ROI **0.13** · net gain €90 · must add **€1,775** of revenue to break even (expects €2,000)
> **Project planned ROI: 0.19 → 0.18 with this action**
> Free-shipping actions so far: **too few closed to say** (fewer than 3)

**The project's planned ROI** counts every action that is not rejected or cancelled and has an expected change: closed actions with their *realised* result, all others with their *expected* one. It is labelled *planned*, never *forecast*: it restates the team's own assumptions, added up.

**The lever's track record** is total actual change over total expected change across that lever's closed actions — *"checkout-friction actions have delivered 60% of what they expected (4 closed)"*. Below three closed actions it says *too few to say* instead of a number. It is the reality check on the estimate the person is typing: the history of their own team, not a model.

The arithmetic is `project_impact()` and `track_record()` in `roi.py`, pure functions like the rest; the route only gathers the rows. The preview **writes nothing** (test 39) — it is a question, not a commitment.

---

## 7 · The portfolio components — 40%

All four built in **Make**, covering the brief's three required types — scheduled, triggered by an event, and with a human approval step. All four reach the app only through its own API, never its database: the two that create something (1 and 2) send events with `POST /api/events`, and 2, 3 and 4 read with `GET /api/metrics`. The app announces changes to Make through the outbox (§4). Make moves data and messages; **the app computes ROI and enforces every rule**. No formula and no decision lives in a Make scenario, where it would be untested and unaudited.

| | Brief type | Make modules | `external_id` | On duplicate | On partial failure |
|---|---|---|---|---|---|
| **1 · Spend and revenue intake** W4 | Scheduled | Schedule Monday → Google Sheets rows for the week → Iterator per KPI → HTTP POST | `"{kpi}:{iso_week}:{value hash}"` | same value: no-op · corrected value: recorded as a correction | re-run is safe: recorded KPIs no-op, missing ones land |
| **2 · KPI drift alert** W5 | Event-triggered | Webhook `measurement.recorded` → signed GET (`off_target`) → Router → HTTP POST | `"{kpi}:{iso_week}"` | one alert per KPI per week; an open drift action gets a task, not a twin | announcement stays in the outbox until Make accepts it; the next measurement re-checks |
| **3 · Approval routing** W7 | Human approval | Webhook `action.in_review` → signed GET → message to the **named reviewer**, who decides signed in to the app · webhook `action.decided` → outcome to requester and owner · weekday schedule → a reminder after 2 business days, escalation after 5 (to the founder, or flagged for the admin when the founder is already the reviewer; never an approval) | n/a — decisions are made once, in the app | a second request is harmless; a second approval is refused | the next morning's reminder covers a lost message |
| **4 · Weekly ROI narrative** W8, written up W11 | Scheduled, AI | Schedule Monday → GET aggregates → AI module → Email or Slack | `"weekly:{iso_week}"`, kept in a Make data store | one report per week | report regenerates, no state lost |

Each gets `docs/portfolio/automation-0N.md` with the business problem (who, how often, how long by hand), the architecture diagram, the verbatim prompts, run screenshots in `docs/portfolio/img/`, and the three failure answers. Detail in [`portfolio/portfolio-plan.md`](portfolio/portfolio-plan.md).

**Automation 4 never sees raw rows.** It aggregates in SQL first and sends only the numbers to the model. Action titles and hypotheses are user input, and user input in a prompt is an injection vector — that reasoning goes in `docs/governance.md`.

---

## 8 · Seed data

The schema is real; only its contents are invented. Without rows there is no interface to screenshot in Week 6, no demo in Week 10, nothing for automation #4 to summarise and nothing to present on 13 January.

**Seed data and test fixtures are different things and must not share a file.**

| | Seed | Fixtures |
|---|---|---|
| Purpose | make the demo credible | make a test deterministic |
| Size | tens of rows | two or three |
| Lives in | `schema/002_seed.sql`, run by an explicit flag | `tests/conftest.py` |
| Lifetime | persists | created and destroyed per test |

A test that depends on demo data breaks every time the demo changes. The seed must never run automatically in production.

### Shape

The seed follows the **hypothetical** Luna Home scenario in [`design/user-group.md`](design/user-group.md): a fictional Spanish homeware store and its agency. It is labelled hypothetical in the data and on screen wherever its origin matters. The worked example in §6 keeps its own store and 40% margin, because it is a test fixture, not seed data.

**One project:** Luna Home, one quarter, budget €15,000 (≈ €5,000 a month, covering advertising, agency labour and creative/development work), `roi_target` **0.20** — a 20% net return on total marketing costs under the existing ROI formula; a hypothetical business target, not an industry benchmark — **contribution margin 35%** (after product costs, discounts, payment fees and fulfilment), €35/hour. The amount the margin produces is labelled **"contribution before marketing costs"**, not "gross profit"; advertising and agency/creative costs are then subtracted once, as the action's investment.

**5 users**, the five people in the scenario, several holding more than one role (§3, "Multiple roles per user" — decided, not yet built):

| Person | Roles |
|---|---|
| Founder | `admin`, `reviewer` — and, as admin, can create actions |
| Ecommerce manager | `requester`, `reviewer` |
| Account manager | `requester`, `owner` — creates coordinated tasks and owns reporting work |
| Paid media specialist | `owner` |
| Freelance designer/developer | `owner` |

Nobody reviews an action they requested or own, whatever their roles, so the founder reviews the ecommerce manager's actions and the ecommerce manager reviews the founder's; with no eligible reviewer, an action stays blocked. Every human role is held by at least one scenario person, so the brief's test account per role comes from the scenario; single-role test accounts may be added to test enforcement, labelled as test-only. Plus **2 `service` accounts**, one for each writing automation (intake, drift alert), with no password.

**13 weeks of measurements** for sessions, conversion rate and AOV — the full quarter, around a baseline of **12,300 sessions a week, 1.8% conversion, €65 AOV** (≈ 221 orders and ≈ €14,400 revenue a week, ≈ €748,000 a year), with realistic week-to-week noise and a visible lift after the actions that worked.

**~24 actions**, spread across every status, every lever and every request type, including three closed ones, so the project page shows realised ROI on day one.

### Timestamps must be backdated — this is the part people get wrong

Spread over **the previous thirteen weeks**. If every row is written with `datetime('now')`, every transition happens in the same second, so cycle time is zero, nothing is ever stuck, the KPI charts are a single point, and automation #4 produces a weekly report that says nothing at all.

### Cases the seed must contain

Not decoration — each one makes a rule or a metric demonstrable:

1. **An action in `assigned` with an open task** — proves the review guard refuses it
2. **An action in `assigned` with no lever** — proves review needs a lever and a hypothesis
3. **An action sitting in `in_review` for 14+ days** — gives the "stuck beyond N days" metric something to report
4. **A rework loop** — `in_review → assigned → in_review`
5. **A rejected action with a note explaining why**
6. **Three actions closed** by a reviewer who is neither requester nor owner — the happy path. One of them is the scenario's **promotional campaign**: €1,500 of advertising plus €400 of creative and agency work, €4,500 of attributed revenue (ROAS 3.0), €1,575 of contribution at 35%, an estimated loss of €325 and ROI −0.17 — the ROAS-versus-ROI contrast. It stays below the project's 0.20 target: a lower target changes no action's result
7. **A closed action labelled `correlated`** — so the interface has to show a weak result honestly. The promotional campaign is a natural candidate: its revenue is attributed, not shown to be incremental
8. **A corrected measurement** — the original row and the correction both present
9. **A target revised mid-quarter** — so the history of targets is visible
10. **Two automation events sharing an `external_id`** — one measurement recorded, proving idempotency
11. **An action in review for three business days whose named reviewer has not decided** — gives automation 3's reminder something to send
12. **An action in review for six business days whose named reviewer is the founder** — once escalation is built, it is flagged for the admin and stays pending; nothing approves it

### Content rules

Invented, but plausible: the kind of actions a real ecommerce team takes — a checkout fix, a prospecting campaign, a bundle launch, a free-shipping threshold test.

**Nothing real.** No real store, no real ad account, no real customers, no real figures. Week 11 covers exactly this, with the Data Protection Commission's guidance, and a public repository is a public repository. Seed passwords are obvious placeholders, hashed the same way real ones would be.

### When

Designed now, written as SQL in **Week 5**, once the schema is final.

---

## 9 · Security surface — what Week 8 should find

Authorisation is what AI-generated CRUD code gets wrong most reliably, because the model checks *authentication* — are you signed in? — and forgets *authorisation* — are you allowed to do this specific thing? The approve and close routes concentrate the classic findings, and in this application the most valuable thing to forge is a result.

| # | Finding | The question that exposes it |
|---|---|---|
| 1 | **IDOR** | Does `POST /requests/42/close` verify the actor against *this* action, or only that a session exists? |
| 2 | **Mass assignment** | Does a form POST containing `status=closed` or `actual_delta=0.05` get written straight into the model, letting an owner grade their own work? |
| 3 | **Client-side-only enforcement** | The Close button is hidden for owners — is the route still open to anyone who curls it? |
| 4 | **Race condition** | Two reviewers closing simultaneously: two audit rows and two different actuals? |
| 5 | **Rewriting history** | Can a measurement or a target be edited in place instead of superseded? The triggers say no; does any route try? |
| 6 | **The forwarded approval** | Automation 3 emails the named reviewer a link. If it is forwarded, can the person who clicks it approve? Test 26 says no — does the route actually call `check_transition()` with the signed-in user? |

Finding 3 is the most common output of the six, and it is why test 15 exists: curl `/approve` as the requester and expect a refusal, not a redirect.

The full threat model — STRIDE on every flow that crosses a trust boundary, as the brief requires — is [`design/stride.md`](design/stride.md). This section is the subset Week 8 should go looking for in the code.

Scanners will not find most of these. Bandit and Semgrep catch injection, hardcoded secrets and unsafe deserialisation; they do not know who is allowed to certify a result. That is the point of Week 8 — the report is triage and judgement, not a tool dump.

`check_transition()` in `lifecycle.py` is the control, the triggers are the backstop, and the tests are the proof the control holds.

---

## 10 · Open questions for the session ❓

1. **The approval deadlock.** ✅ *Decided 28 October 2026:* the rule stays — the named reviewer is neither the requester nor the owner, for approving and for closing. In the hypothetical scenario the founder reviews the ecommerce manager's actions and the ecommerce manager reviews the founder's. **If no eligible reviewer exists, the action stays blocked**: no admin override, no auto-approval, and silence never counts as approval. An overdue decision is reminded and escalated (automation 3), never bypassed. The question was also put to the lecturer on the forum; his answer may reopen it.
2. **Who closes an action.** ✅ *Decided 28 October 2026:* the **named reviewer** certifies the result and closes the action, provided they are neither its requester nor its owner. `admin` status alone never authorises closing, and the requester does not sign off their own request. Others — in the hypothetical scenario, the account manager — may prepare the results analysis without certifying it.
3. **Measurement granularity.** Weekly is the recommendation: thirteen points a quarter is enough, and daily entry is a chore nobody keeps up.
4. **Corrections through the intake.** A corrected value from the Sheet is recorded as a correction because its `external_id` carries a hash of the value. Is that the right behaviour, or should corrections only ever be made by hand?
5. **ROI on screen.** A ratio (3.29) or a percentage (329%)?
6. **Password storage.** ✅ *Decided 28 October 2026 — my project design decision, not a requirement set by the lecturer:* neither the Session 8 slides nor the Week 8 Directed Learning sheet mandates scrypt, Argon2id or any other algorithm. Passwords are stored with **Werkzeug's scrypt**, chosen because Werkzeug is already a pinned dependency, so no new package is added.
   - **Intended use:** `werkzeug.security.generate_password_hash(password)` when a password is set, storing only the result in `users.password_hash`; `check_password_hash(stored_hash, attempt)` at sign-in. The password itself is never stored or logged.
   - **Verify when authentication is implemented:** the method and parameters the installed Werkzeug actually produces. On 28 October, Werkzeug 3.1.9 in this project's environment produced `scrypt:32768:8:1` (N = 32,768, r = 8, p = 1). If the version or the default changes, the spec records the new method string.
   - **Review in the Week 8 security audit:** compare those parameters with the current OWASP Password Storage Cheat Sheet, and either raise them (by passing an explicit `method`) or record why the default is kept. Argon2id (`argon2-cffi`) stays the alternative if the audit finds scrypt's settings inadequate.
   - **Not built yet:** no authentication code exists; this records the design only.
7. **The delete rule.** The Week 5 sheet asks it directly: *"If you delete a project, what should happen to its tasks?"* Here nothing is ever deleted — actions are cancelled, numbers are superseded. Is "the question does not arise" defensible, or should a project be archivable?
8. **Scale of seed data.** ✅ *Decided 28 October 2026:* one quarter of the hypothetical Luna Home scenario, as designed in §8 — five people, 13 weeks of measurements, ~24 actions. Fictional throughout, so it implies no real customer data.
9. **Retention periods.** Proposed in [`design/gdpr.md`](design/gdpr.md): the record for the project period plus 24 months, a departed user pseudonymised after 12 months, delivery queues purged after 90 days. To be confirmed in the Week 11 governance document.
10. **The real user group.** The brief asks for a named group with a real problem. The design now uses a **hypothetical** agency–client scenario, described in [`design/user-group.md`](design/user-group.md). It supports the prototype; it is **not evidence from real users** and is not validated research. Real-user evidence remains **outstanding**, and whether a hypothetical scenario is acceptable is a question for the lecturer.
11. **Lecturer agreement.** An own idea must be agreed before building starts — before the 28 October lab generates anything.
12. **One role per person.** ✅ *Decided 28 October 2026:* a person may hold several roles (§3, "Multiple roles per user"), and the approval restriction applies by identity — nobody reviews an action they requested or own, `admin` included. In the hypothetical scenario: founder `admin` + `reviewer`; ecommerce manager `requester` + `reviewer`; account manager `requester` + `owner`; paid media specialist and designer/developer `owner`. **Not yet built:** the schema, `lifecycle.py`, route checks and tests listed in §3 change when authentication is built.

**Agreed future requirements** (28 October 2026), recorded now and built in their planned weeks: actions **above €500**, and any budget increase, need the founder's approval (amount-based routing, a separate rule from the monthly budget) — and **if the founder requested or owns such an action, it stays blocked**, because that approval would break the identity rule and the ecommerce manager cannot substitute for it; a **monthly budget of about €5,000** never overrides the reviewer rules; and automation 3 **reminds after 2 business days and escalates after 5**, to the founder, or flags the action for the admin when the founder is already its reviewer. Nothing is ever auto-approved.

---

## 11 · Out of scope

Stated so the generated code does not acquire them:

- **No formula builder** and no user-defined KPI trees — the tree in §3 is fixed
- **No live connections** to Meta, Google Ads, Shopify or any ad platform inside the app — figures arrive by hand or through automation #1
- **No causal attribution** — no marketing mix models, no incrementality testing. Results carry a confidence label instead
- **No forecasting**, LTV or cohort analysis
- **No pricing or discount levers** — margin is a fixed project setting
- **No multiple currencies, no multi-tenancy** — one store, one team, one database
- No Gantt or dependencies, no timesheets — an action records its total hours as a cost, nothing finer
- No chat or threaded comments, no file attachments, no email sent by the app itself — its only outward call is the signed, ids-only announcement to Make — no auto-assignment beyond a default owner per type, no public API beyond the two machine routes, no mobile app
- No approve or reject buttons in emails: approval is always made signed in to the app, by the named reviewer
