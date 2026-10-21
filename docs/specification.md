# Specification — MarketingOps

**Draft.** Written for Week 3 Block A, to be refined in the live session on 28 October. Open questions are marked ❓ and are deliberately unresolved.

Companion document: [`project-definition.md`](project-definition.md) covers the why, the scope boundaries and the weekly plan. This one is the technical surface.

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
| Tests | pytest | | Week 7 |
| Lint | Ruff | with `ruff.toml` | Week 7 |
| Security | Bandit · Semgrep · pip-audit | | Week 8 |
| WSGI (prod) | Gunicorn | | Week 9 |
| Packaging | Docker, multi-stage, non-root | image < 250 MB | Week 9 |
| Hosting | AWS Lightsail container service | `linux/amd64`, `eu-west-1` | Week 10 |

No ORM. Raw SQL with parameterised queries — the Week 5 brief requires finding and removing string-formatted SQL, which is only meaningful if the SQL is visible.

---

## 2 · Component list

```
lowcode-project/
├── app.py                    # application factory, config load, blueprint registration
├── config.py                 # settings from environment; no secrets in source
├── db.py                     # connection helper; sets PRAGMA foreign_keys=ON per connection
├── lifecycle.py              # ALLOWED transition map + check_transition()   ← core logic
├── auth.py                   # login, logout, session, @role_required decorator
│
├── models/
│   ├── users.py              # lookup, role checks
│   ├── requests.py           # create, read, list by owner/status, update status
│   ├── transitions.py        # append-only writes; timeline reads; metric aggregates
│   ├── tasks.py              # add, complete, count open per request
│   ├── checks.py             # mark passed, list required-by-type, all-passed test
│   └── events.py             # automation_events insert with idempotency
│
├── routes/
│   ├── auth_routes.py        # /login, /logout
│   ├── request_routes.py     # request CRUD and the five lifecycle actions
│   ├── task_routes.py        # /requests/<id>/tasks, /tasks/<id>/complete
│   ├── check_routes.py       # /requests/<id>/checks/<key>
│   └── api_routes.py         # /api/events, /api/metrics
│
├── templates/
│   ├── base.html             # layout, nav, flash messages, landmarks
│   ├── login.html
│   ├── requests_list.html    # "my queue"
│   ├── request_new.html      # the submission form
│   ├── request_detail.html   # detail + actions + timeline
│   ├── _timeline.html        # partial: the transition history
│   └── _flash.html           # partial: status messages
│
├── static/app.css            # the little Tailwind cannot do
├── schema/001_initial.sql
├── tests/                    # see §6
├── security/                 # scan evidence, Week 8
└── docs/
```

Roughly twenty source files. That is "a real multi-file application" without being a framework.

**Why `lifecycle.py` is a separate module with no Flask import:** it is pure functions over plain data, so Week 7 can test every transition rule without spinning up an app or a database. It is the single most testable thing in the project and it should stay that way.

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

### `requests`

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `title` | TEXT | NOT NULL |
| `description` | TEXT | NOT NULL DEFAULT '' |
| `request_type` | TEXT | CHECK in (`content`,`campaign`,`landing_page`,`data`,`lead`,`other`) |
| `status` | TEXT | CHECK in (`submitted`,`assigned`,`in_review`,`approved`,`rejected`,`cancelled`) |
| `priority` | TEXT | DEFAULT `normal`, CHECK in (`low`,`normal`,`high`) |
| `requester_id` | INTEGER | FK → users |
| `owner_id` | INTEGER | FK → users, nullable |
| `due_date` | TEXT | nullable |
| `created_at` | TEXT | |

Table-level CHECK: a request may only be `submitted` or `cancelled` while `owner_id IS NULL`.

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

`id` · `source` CHECK in (`paid_media`,`performance`,`assistant`) · `external_id` TEXT · `payload` TEXT (JSON) · `request_id` FK nullable · `received_at` · **UNIQUE `(source, external_id)`**

---

## 4 · Routes

| Method | Path | Who | Does |
|---|---|---|---|
| GET/POST | `/login` | anyone | session start |
| POST | `/logout` | signed in | session end |
| GET | `/requests` | signed in | my queue: owned requests + assigned tasks, by due date |
| GET | `/requests/new` | signed in | the form |
| POST | `/requests` | signed in | create → `submitted`, writes transition #1 |
| GET | `/requests/<id>` | signed in | detail, available actions, timeline |
| POST | `/requests/<id>/assign` | owner, admin | set `owner_id` → `assigned` |
| POST | `/requests/<id>/review` | owner, admin | → `in_review`, **refused if open tasks** |
| POST | `/requests/<id>/approve` | reviewer, admin | → `approved`, **refused if requester or owner, or checks unpassed** |
| POST | `/requests/<id>/reject` | reviewer, admin | → `rejected` |
| POST | `/requests/<id>/cancel` | requester, admin | → `cancelled` |
| POST | `/requests/<id>/tasks` | owner, admin | add task |
| POST | `/tasks/<id>/complete` | assignee, owner, admin | mark done |
| POST | `/requests/<id>/checks/<key>` | reviewer, admin | mark check passed |
| POST | `/api/events` | HMAC signature | automation intake, idempotent |
| GET | `/api/metrics` | HMAC signature | aggregates from transitions |

Every lifecycle route goes through `check_transition()` before writing. No route writes a status directly.

### `POST /api/events`

```json
{ "source": "paid_media", "external_id": "<platform id>", "payload": { } }
```

Header `X-Signature`: HMAC-SHA256 of the raw body with a shared secret from the environment.

| Case | Response |
|---|---|
| Valid, new | `201` + request id |
| Valid, already seen | `200`, no-op |
| Bad signature | `401` |
| Malformed / missing fields | `400` — never a 500 |

---

## 5 · Templates

| Template | Shows |
|---|---|
| `base.html` | nav, flash region, skip link, landmarks |
| `login.html` | email + password, labelled inputs |
| `requests_list.html` | my queue; status as text *and* colour, never colour alone |
| `request_new.html` | title, type, priority, due date, description |
| `request_detail.html` | fields, the action buttons the viewer is actually allowed, task list, check list |
| `_timeline.html` | every transition: who, from, to, when, note |
| `_flash.html` | success and error messages |

**Week 8 trap to avoid:** `request_detail.html` hides buttons the viewer may not use. Hiding a button is not authorisation. Every route re-checks server-side, and there will be a test that curls `/approve` as the requester and expects a refusal.

---

## 6 · Tests

Week 7 asks for at least eight covering valid, invalid, empty and boundary input.

**`test_lifecycle.py`** — no app, no database
1. Every legal transition is allowed
2. Every illegal transition is refused (`submitted → approved` etc.)
3. A requester cannot approve their own request
4. The owner cannot approve work they did
5. A wrong role cannot approve
6. An independent reviewer can
7. `assigned → assigned` is legal and still records a transition

**`test_requests.py`**
8. A request with an open task cannot enter review
9. A request with unpassed required checks cannot be approved
10. `requests.status` always equals the latest transition's `to_status`

**`test_api_events.py`**
11. Valid signed event creates a request
12. The same `external_id` twice creates one request, not two
13. A bad signature returns 401
14. An empty body, a missing field and a 10,000-character name each return 400, not 500

**`test_auth.py`**
15. `POST /requests/<id>/approve` by the requester returns 403 even though the button is hidden

Fifteen. Deliberately more than eight, and all of 1–7 run in milliseconds.

---

## 7 · The portfolio components — 40%

All four built in **Make**. All four reach the app only through `POST /api/events`.

| | Make modules | `external_id` | On duplicate | On partial failure |
|---|---|---|---|---|
| **1 · Lead intake** W4 | Webhook → Filter (qualifying fields) → HTTP POST | platform lead id | app no-ops | Make retries; idempotency makes that safe |
| **2 · Daily digest** W5 | Schedule 08:00 → HTTP GET `/api/metrics` → Formatter → Email | n/a (read-only) | n/a | no write, so a failure loses nothing |
| **3 · Threshold alert** W7 | Schedule → Fetch export → Router (breach only) → HTTP POST | `"{metric}:{date}"` | one alert per metric per day | logged, retried next run |
| **4 · Weekly summary** W11 | Schedule Monday → GET aggregates → LLM narrative → Post | `"weekly:{iso_week}"` | one report per week | report regenerates, no state lost |

Each gets `docs/portfolio/automation-0N.md` with the business problem (who, how often, how long by hand), the architecture diagram, the verbatim prompts, run screenshots in `docs/portfolio/img/`, and the three failure answers.

**Automation 4 never sees raw rows.** It aggregates in SQL first and sends only the numbers to the model. Request titles are user input, and user input in a prompt is an injection vector — that reasoning goes in `docs/governance.md`.

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

**8 users:** 2 requesters, 3 owners, 2 reviewers, 1 admin. Enough that "the owner cannot approve their own work" has someone left to approve.

**~24 requests**, spread across every status and every type:

| Status | Count | Type | Count |
|---|---|---|---|
| `submitted` | 4 | `content` | 7 |
| `assigned` | 6 | `campaign` | 6 |
| `in_review` | 3 | `landing_page` | 4 |
| `approved` | 8 | `lead` | 4 |
| `rejected` | 2 | `data` | 3 |
| `cancelled` | 1 | | |

### Timestamps must be backdated — this is the part people get wrong

Spread over **the previous eight weeks**. If every row is written with `datetime('now')`, every transition happens in the same second, so cycle time is zero, nothing is ever stuck, and automation #4 produces a weekly report that says nothing at all.

Approved requests should show a realistic spread of 2 to 14 days end to end.

### Cases the seed must contain

Not decoration — each one makes a rule or a metric demonstrable:

1. **A request in `assigned` with an open task** — proves the review guard refuses it
2. **A request sitting in `in_review` for 14+ days** — gives the "stuck beyond N days" metric something to report
3. **A rework loop** — `in_review → assigned → in_review`, so the timeline shows a round trip
4. **A reassignment** — `assigned → assigned` with a different owner, the transition that does not change status
5. **A rejected request with a note explaining why**
6. **An approved request where the reviewer is neither requester nor owner** — the happy path, provable
7. **Two automation events sharing an `external_id`** — one request created, proving idempotency
8. **Requests of each type with their type-specific review checks**, some passed, some not

### Content rules

Invented, but plausible. Marketing request titles of the kind a real team raises — a one-pager for an outbound push, a landing page for a webinar, a pricing copy refresh.

**Nothing real.** No real client names, no real campaign data, no real email addresses, no real figures. Week 11 covers exactly this, with the Data Protection Commission's guidance, and a public repository is a public repository. Seed passwords are obvious placeholders, hashed the same way real ones would be.

### When

Designed now, written as SQL in **Week 5**, once the schema is final. Writing it earlier means rewriting it after the 28th.

---

## 9 · Security surface — what Week 8 should find

Authorisation is what AI-generated CRUD code gets wrong most reliably, because the model checks *authentication* — are you signed in? — and forgets *authorisation* — are you allowed to do this specific thing? The approve route concentrates four classic findings in one handler.

| # | Finding | The question that exposes it |
|---|---|---|
| 1 | **IDOR** | Does `POST /requests/42/approve` verify the actor against *this* request, or only that a session exists? |
| 2 | **Mass assignment** | Does a form POST containing `status=approved` get written straight into the model, letting a requester skip the workflow? |
| 3 | **Client-side-only enforcement** | The Approve button is hidden for non-reviewers — is the route still open to anyone who curls it? |
| 4 | **Race condition** | Two reviewers approving simultaneously: two audit rows and an ambiguous history? |

Finding 3 is the most common output of the four, and it is why test 15 exists: curl `/approve` as the requester and expect a refusal, not a redirect.

Scanners will not find most of these. Bandit and Semgrep catch injection, hardcoded secrets and unsafe deserialisation; they do not know who is allowed to approve what. That is the point of Week 8 — the report is triage and judgement, not a tool dump.

`check_transition()` in `lifecycle.py` is the control, and the tests are the proof the control holds.

---

## 10 · Open questions for the session ❓

1. **The approval deadlock.** Owner cannot approve own work. In a three-person team, nobody may be eligible. Admin override that logs loudly, or drop the rule?
2. **Password storage.** Flask has no built-in. `werkzeug.security` is already a dependency — likely the answer, but Week 8 should confirm the algorithm is current.
3. **Delete rule.** Nothing is ever deleted here; `cancelled` is a status. Week 5 requires a decision anyway — is "the question does not arise" an acceptable answer, or should there be a hard delete for data-protection requests?
4. **Scale of seed data.** Enough realistic rows to make the Week 10 demo convincing without implying real customer data.

---

## 11 · Out of scope

Stated so the generated code does not acquire them: no Gantt or dependencies, no time tracking, no chat or threaded comments, no file attachments, no multi-tenancy, no email sent by the app itself, no auto-assignment beyond a default owner per type, no public API beyond the two machine routes, no mobile app.
