# Project definition

Working name: **MarketingOps**, with the ROI layer
Repository: `lowcode-project` · Docker image: `lowcode-app`
Drafted 2026-10-21, reshaped 2026-10-22 for the ROI layer. This is the Week 3 Block A draft, to be refined in the live session on 28 October; the technical detail is in `docs/specification.md`.

---

## 1 · The application — the 60%

### What it is, in one sentence

A system of record for marketing work in which every action has to say which KPI it is meant to move, by how much and at what cost — and is closed with what it actually achieved, so the project's real ROI is on the record rather than in someone's memory.

### Why ROI, and why it is not ROAS

Most marketing dashboards report ROAS: revenue divided by ad spend. It flatters. It ignores margin and it ignores people time, so a campaign can show a healthy ROAS and lose money. This application computes **ROI = (incremental gross profit − investment) ÷ investment**, with investment counting hours as well as cash. That difference is the project's credibility point, and it comes from RevOps practice, not from the course.

### Who uses it

| Role | Who | May do |
|---|---|---|
| `requester` | Founder, sales, product | Open actions, view their own, cancel their own |
| `owner` | Marketing specialist | Own an action, add and complete tasks, record measurements, send to review |
| `reviewer` | Marketing lead, finance, brand | Approve, reject or close — only if not the requester and not the owner |
| `admin` | Ops | Everything — but bound by the same rule: cannot approve or close an action they raised or worked on. Whether admins get a logged override for small teams is an **open decision** (`specification.md` §10) |

### The lifecycle

```
submitted → assigned → in_review → approved → closed
                ↑           │
                └───────────┘   (rework)
                            └──→ rejected
any open state → cancelled
```

Terminal states: `closed`, `rejected`, `cancelled`.
`assigned → assigned` is legal: that is reassignment to a different owner, and it still writes a transition.
`approved → closed` records the actual result and a confidence label — `holdout`, `before_after` or `correlated` — and is signed off by someone independent of the work.

### The KPI tree

Fixed, one template, for an online store over one period:

```
ROI = (incremental gross profit − investment) ÷ investment
└── gross profit = revenue × margin
    └── revenue = sessions × conversion rate × average order value
```

Each action pulls one **lever**, and each lever moves exactly one of the three leaf KPIs.

### Entities

`users` · `projects` · `kpis` · `levers` · `requests` (the actions) · `request_transitions` · `kpi_targets` · `kpi_measurements` · `tasks` · `review_checks` · `automation_events`

DDL in `schema/001_initial.sql`, finalised in Week 5. The invariant that defines the project: **the record cannot be quietly rewritten.** `request_transitions`, `kpi_targets` and `kpi_measurements` are append-only, enforced by triggers that abort `UPDATE` and `DELETE`; a correction is a new row that supersedes the old one.

### Routes

**Auth** — `GET /login` · `POST /login` · `POST /logout`

**Projects** — `GET /projects` · `POST /projects` · `GET /projects/<id>` · `POST /projects/<id>/targets` · `POST /projects/<id>/measurements`

**Actions**
- `GET /requests` — my queue · `GET /requests/new` · `POST /requests`
- `GET /requests/<id>` — detail, results and the full timeline
- `POST /requests/<id>/assign` · `/review` · `/approve` · `/reject` · `/close` · `/cancel`

**Tasks and checks** — `POST /requests/<id>/tasks` · `POST /tasks/<id>/complete` · `POST /requests/<id>/checks/<key>`

**Machine interface**
- `POST /api/events` — automation intake. HMAC-signed, idempotent on `(source, external_id)`
- `GET /api/metrics` — KPIs against target, ROI, cycle times

### The invariants worth testing

1. An action cannot enter review while it has an incomplete task, or without a lever and a hypothesis.
2. It cannot be approved while any required check for its type is unpassed.
3. Nobody approves or closes their own action, and the owner who did the work does not either.
4. ROI is computed from gross profit and counts people time; zero investment has no ROI rather than an infinite one.
5. A number on the record is never edited — only superseded.

### Explicitly out of scope

Anything not listed as in scope is out, and these in particular:

- No formula builder or user-defined KPI trees
- No live connections to ad platforms or the shop inside the app
- No causal attribution, forecasting, LTV or cohort analysis
- No pricing or discount levers — margin is a project setting
- No Gantt charts, dependencies or timesheets — an action records its total hours as a cost
- No chat or threaded comments — a note on a transition is the whole comment model
- No file attachments, no multiple currencies, no multi-tenancy
- No email from the app itself — that is the automations' job
- No mobile app, no public API beyond the two machine routes above

---

## 2 · The portfolio — the 40%

Four automations, each documented as `docs/portfolio/automation-0N.md` with: the business problem (who does it, how often, how long it takes), an architecture diagram, the tools and trigger type, the verbatim prompts, screenshots of it running, and honest answers to the three failure questions. Detail in `docs/portfolio/portfolio-plan.md`.

**Built in Make** (recommended by the course: free tier allows multi-step scenarios and 1,000 operations; Zapier's free tier caps at two steps).

**The boundary that applies to all four:** they talk to the application only through its API — `POST /api/events` for the two that create something, `GET /api/metrics` for the two that report. None of them touches the database directly, and none of them computes ROI: Make moves data, the app does the maths. From layer 38 of the influence model — *do not let a recommendation silently become an unrestricted write action.*

They form one loop with the application: spend arrives → the app records it → a KPI drifts → an action is opened → it is approved, done and closed → the app computes realised ROI → the Monday report explains it.

| | Automation | Week | Route |
|---|---|---|---|
| 1 | **Spend and revenue intake** — a weekly platform export becomes measurements | 4 | `POST /api/events` |
| 2 | **Daily digest** — KPIs against target, actions waiting for review or closing | 5 | `GET /api/metrics` |
| 3 | **KPI drift alert** — a KPI off target opens an action, or adds a task to the open one | 7 | both |
| 4 | **Weekly ROI narrative** — an AI writes the summary from aggregates only | 8 / 11 | `GET /api/metrics` |

---

## 3 · What lands in the repository, week by week

| Week | Date | What is committed |
|---|---|---|
| 1 ✅ | 14 Oct | `app.py` · `requirements.txt` · `.gitignore` · `README.md` with the project note |
| 2 ✅ | 21 Oct | `experiments/week02/` raw outputs from three tools · `docs/week02-tool-comparison.md` with measured scores and a reasoned choice |
| 3 | 28 Oct | `docs/specification.md` with the ROI layer · `lifecycle.py` and `roi.py` · multi-file app generated from the spec, on a branch, merged via PR · `docs/week03-review.md` · clean-clone fixes |
| 4 | 4 Nov | the `POST /api/events` handler for spend and revenue · `docs/portfolio/automation-01.md` · `docs/portfolio/img/` |
| 5 | 11 Nov | `schema/001_initial.sql` final · `docs/data-model.md` with ER diagram and the delete rule · CRUD with parameterised queries · string-formatted SQL removed · `automation-02.md` begun |
| 6 | 18 Nov | Templates: responsive, accessible, Tailwind; the project page with KPI charts · `docs/week06-ui-review.md` · before/after screenshots |
| 7 | 25 Nov | `ruff.toml` · `tests/` with the 23 tests · `docs/week07-bugs.md` · `automation-03.md` |
| 8 | 2 Dec | `security/` scan evidence · `docs/security-report.md` with before/after table · dependencies upgraded · automation 4 built |
| 9 | 9 Dec | `Dockerfile` multi-stage, non-root, under 250 MB · `.dockerignore` · `docker-compose.yml` with Postgres |
| 10 | 16 Dec | `docs/deployment.md` including teardown · live HTTPS URL in `README.md` |
| 11 | 6 Jan | `docs/governance.md` · `automation-04.md` · **project submitted** |
| 12 | 13 Jan | Presentation · 500-word reflection · two peer reviews · **portfolio submitted** |

---

## 4 · Decisions still owed

1. **The approval deadlock.** The owner who did the work cannot approve or close it. In a three-person team that can leave nobody eligible. Resolve as an admin override that logs loudly, or drop the rule — and write the reasoning into the governance document either way.
2. **Who certifies results.** Reviewer, as drafted, or the requester who asked for them?
3. **The delete rule.** Week 5 requires this to be decided by hand, on paper, not by an AI — and the sheet asks it about projects directly. Nothing is ever deleted here; is "the question does not arise" defensible, or should a project be archivable?
4. **The problem statement.** The 150 words in the README must describe something actually lived. Week 12 asks what is in the repository that could not be explained in an interview.
5. **The real manual process for automation 1.** The Week 4 sheet: *"Bring a real one. Contrived scenarios are obvious and they mark badly."* Who copies platform numbers by hand, how often, and how long it takes — yours to supply.
6. **An industry problem.** Whether this attaches to a real company's process, via the Industry Engagement Forum. Ask on the Week 3 forum post.
