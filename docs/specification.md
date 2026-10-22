# Specification — MarketingOps, with the ROI layer

**Draft.** Written for Week 3 Block A, reshaped on 22 October for the ROI layer, to be refined in the live session on 28 October. Open questions are marked ❓ and are deliberately unresolved.

> **The pitch:** every piece of marketing work has to justify itself, and the record shows whether it did.

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
│   └── events.py             # automation_events insert with idempotency
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
| `password_hash` | TEXT | NOT NULL ❓ *added at Week 3; Week 8 will check the algorithm* |
| `role` | TEXT | NOT NULL, CHECK in (`requester`,`owner`,`reviewer`,`admin`) |
| `is_active` | INTEGER | NOT NULL DEFAULT 1 |
| `created_at` | TEXT | ISO 8601 UTC |

### `projects`

One store over one period, usually a quarter.

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | TEXT | NOT NULL |
| `period_start`, `period_end` | TEXT | NOT NULL, end after start |
| `budget_eur` | REAL | ≥ 0 |
| `roi_target` | REAL | e.g. 3.0 — €3 net per €1 invested |
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
| `due_date` | TEXT | nullable |
| `lever_id` | INTEGER | FK → levers — required before review |
| `hypothesis` | TEXT | required before review — *"removing forced sign-up lifts conversion by 0.3 points"* |
| `expected_delta` | REAL | in the lever's KPI unit — sessions +8000 · conversion +0.003 · AOV +3.00 |
| `cost_eur` | REAL | cash, ≥ 0, default 0 |
| `cost_hours` | REAL | people time, ≥ 0, default 0 |
| `window_start`, `window_end` | TEXT | the measurement window |
| `actual_delta` | REAL | required to close |
| `confidence` | TEXT | required to close, CHECK in (`holdout`,`before_after`,`correlated`) |
| `created_at` | TEXT | |

Table-level CHECKs: a request may only be `submitted` or `cancelled` while `owner_id IS NULL`; a request may only be `closed` with `actual_delta` and `confidence` set.

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

---

## 4 · Routes

| Method | Path | Who | Does |
|---|---|---|---|
| GET/POST | `/login` | anyone | session start |
| POST | `/logout` | signed in | session end |
| GET | `/projects` | signed in | list |
| POST | `/projects` | admin | create |
| GET | `/projects/<id>` | signed in | the KPI tree, KPIs against target, actions with expected and realised ROI |
| POST | `/projects/<id>/targets` | admin | a new target version — never an edit |
| POST | `/projects/<id>/measurements` | owner, admin | a weekly measurement or a correction — never an edit |
| GET | `/requests` | signed in | my queue: owned actions + assigned tasks, by due date |
| GET | `/requests/new` | signed in | the form |
| POST | `/requests` | signed in | create → `submitted`, writes transition #1 |
| GET | `/requests/<id>` | signed in | detail, permitted actions, expected and actual results, timeline |
| POST | `/requests/<id>/assign` | owner, admin | set `owner_id` → `assigned` |
| POST | `/requests/<id>/review` | owner, admin | → `in_review`, **refused if open tasks, or no lever and hypothesis** |
| POST | `/requests/<id>/approve` | reviewer, admin | → `approved`, **refused if requester or owner, or checks unpassed** |
| POST | `/requests/<id>/reject` | reviewer, admin | → `rejected` |
| POST | `/requests/<id>/close` | reviewer, admin | → `closed` with `actual_delta` and `confidence`, **refused if requester or owner** |
| POST | `/requests/<id>/cancel` | requester, admin | → `cancelled` |
| POST | `/requests/<id>/tasks` | owner, admin | add task |
| POST | `/tasks/<id>/complete` | assignee, owner, admin | mark done |
| POST | `/requests/<id>/checks/<key>` | reviewer, admin | mark check passed |
| POST | `/api/events` | HMAC signature | automation intake, idempotent |
| GET | `/api/metrics` | HMAC signature | aggregates: KPIs against target, ROI, cycle times |

Every lifecycle route goes through `check_transition()` before writing. No route writes a status directly.

**Every status change is one transaction.** The route updates `requests.status` and inserts the matching `request_transitions` row inside a single database transaction: both are written, or neither is. Without that, a failure between the two writes leaves a request whose status says one thing and whose history says another — an approval with no record of who approved it, which is the one thing this application exists to prevent. Test 10 checks the result; the transaction is what guarantees it. Closing writes `actual_delta`, `confidence` and the transition in the same transaction.

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

---

## 5 · Templates

| Template | Shows |
|---|---|
| `base.html` | nav, flash region, skip link, landmarks |
| `login.html` | email + password, labelled inputs |
| `project_detail.html` | the KPI tree; each KPI against target, as text *and* a chart; actions with expected and realised ROI; project ROI against `roi_target` |
| `requests_list.html` | my queue; status as text *and* colour, never colour alone |
| `request_new.html` | title, type, priority, due date, description, lever, hypothesis, expected change, cost in euros and hours, measurement window |
| `request_detail.html` | fields; expected ROI; once closed, actual result, confidence and realised ROI; the action buttons the viewer is actually allowed; tasks; checks |
| `_timeline.html` | every transition: who, from, to, when, note |
| `_flash.html` | success and error messages |

**ROI is shown with its basis.** Every ROI figure on screen says whether it is expected or realised and, if realised, its confidence label. A `correlated` result is never displayed as if it were proven.

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

Twenty-three. Deliberately more than eight, and 1–7 and 16–20 run in milliseconds.

### The worked example — the numbers the tests use

Baseline for one 30-day window: 50,000 sessions · 2.0% conversion · €60 AOV = €60,000 revenue. Margin 40%. People time €35/hour.

| Action | Lever → KPI | Expected change | Revenue | Gross profit | Investment | ROI | ROAS |
|---|---|---|---|---|---|---|---|
| A · Remove forced sign-up | checkout friction → conversion | +0.3 points | €9,000 | €3,600 | €840 (24 h) | **3.29** | n/a |
| B · Meta prospecting | paid prospecting → sessions | +8,000 | €9,600 | €3,840 | €5,350 (€5,000 + 10 h) | **−0.28** | 1.92 |
| C · Two bundles | bundles → AOV | +€3.00 | €3,000 | €1,200 | €1,080 (€800 + 8 h) | **0.11** | 3.75 |
| **Project** | | | €21,600 | €8,640 | €7,270 | **0.19** | |

Already verified against `roi.py`. B looks healthy on ROAS and loses money; A costs no cash and returns the most. That contrast is the argument of the whole application.

---

## 7 · The portfolio components — 40%

All four built in **Make**. All four reach the app only through its own API, never its database: the two that create something (1 and 3) send events with `POST /api/events`, and the two that report (2 and 4) read aggregates with `GET /api/metrics`. Make moves data; **the app computes ROI**. No formula lives in a Make scenario, where it would be untested and unaudited.

| | Make modules | `external_id` | On duplicate | On partial failure |
|---|---|---|---|---|
| **1 · Spend and revenue intake** W4 | Schedule Monday → Google Sheets rows for the week → Iterator per KPI → HTTP POST | `"{kpi}:{iso_week}:{value hash}"` | same value: no-op · corrected value: recorded as a correction | re-run is safe: recorded KPIs no-op, missing ones land |
| **2 · Daily digest** W5 | Schedule 08:00 → HTTP GET `/api/metrics` → Formatter → Email | n/a (read-only) | two identical emails, nothing written | no write, so a failure loses nothing |
| **3 · KPI drift alert** W7 | Schedule Monday, after #1 → GET `/api/metrics` → Router (off target only) → HTTP POST | `"{kpi}:{iso_week}"` | one alert per KPI per week; an open drift action gets a task, not a twin | logged, retried next run |
| **4 · Weekly ROI narrative** W8, written up W11 | Schedule Monday → GET aggregates → AI module → Email or Slack | `"weekly:{iso_week}"`, kept in a Make data store | one report per week | report regenerates, no state lost |

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

**One project:** a fictional online store, one quarter, budget €20,000, `roi_target` 3.0, margin 40%, €35/hour.

**8 users:** 2 requesters, 3 owners, 2 reviewers, 1 admin. Enough that "the owner cannot sign off their own work" has someone left to sign it off.

**13 weeks of measurements** for sessions, conversion rate and AOV — the full quarter, with realistic week-to-week noise and a visible lift after the actions that worked.

**~24 actions**, spread across every status, every lever and every request type, including the three in the worked example (§6), closed, so the project page shows A, B and C with their realised ROI on day one.

### Timestamps must be backdated — this is the part people get wrong

Spread over **the previous thirteen weeks**. If every row is written with `datetime('now')`, every transition happens in the same second, so cycle time is zero, nothing is ever stuck, the KPI charts are a single point, and automation #4 produces a weekly report that says nothing at all.

### Cases the seed must contain

Not decoration — each one makes a rule or a metric demonstrable:

1. **An action in `assigned` with an open task** — proves the review guard refuses it
2. **An action in `assigned` with no lever** — proves review needs a lever and a hypothesis
3. **An action sitting in `in_review` for 14+ days** — gives the "stuck beyond N days" metric something to report
4. **A rework loop** — `in_review → assigned → in_review`
5. **A rejected action with a note explaining why**
6. **Actions A, B and C closed**, by a reviewer who is neither requester nor owner — the happy path and the ROAS-versus-ROI contrast
7. **A closed action labelled `correlated`** — so the interface has to show a weak result honestly
8. **A corrected measurement** — the original row and the correction both present
9. **A target revised mid-quarter** — so the history of targets is visible
10. **Two automation events sharing an `external_id`** — one measurement recorded, proving idempotency

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

Finding 3 is the most common output of the five, and it is why test 15 exists: curl `/approve` as the requester and expect a refusal, not a redirect.

Scanners will not find most of these. Bandit and Semgrep catch injection, hardcoded secrets and unsafe deserialisation; they do not know who is allowed to certify a result. That is the point of Week 8 — the report is triage and judgement, not a tool dump.

`check_transition()` in `lifecycle.py` is the control, the triggers are the backstop, and the tests are the proof the control holds.

---

## 10 · Open questions for the session ❓

1. **The approval deadlock.** The owner cannot approve or close their own work. In a three-person team, nobody may be eligible. Admin override that logs loudly, or drop the rule? It now applies to closing as well as approving.
2. **Who closes an action.** Drafted as reviewer or admin, independent of the work. Should the requester — who asked for the result — sign it off instead?
3. **Measurement granularity.** Weekly is the recommendation: thirteen points a quarter is enough, and daily entry is a chore nobody keeps up.
4. **Corrections through the intake.** A corrected value from the Sheet is recorded as a correction because its `external_id` carries a hash of the value. Is that the right behaviour, or should corrections only ever be made by hand?
5. **ROI on screen.** A ratio (3.29) or a percentage (329%)?
6. **Password storage.** Flask has no built-in. `werkzeug.security` is already a dependency — likely the answer, but Week 8 should confirm the algorithm is current.
7. **The delete rule.** The Week 5 sheet asks it directly: *"If you delete a project, what should happen to its tasks?"* Here nothing is ever deleted — actions are cancelled, numbers are superseded. Is "the question does not arise" defensible, or should a project be archivable?
8. **Scale of seed data.** Enough realistic rows to make the Week 10 demo convincing without implying real customer data.

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
- No chat or threaded comments, no file attachments, no email sent by the app itself, no auto-assignment beyond a default owner per type, no public API beyond the two machine routes, no mobile app
