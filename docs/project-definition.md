# Project definition

Working name: **MarketingOps**
Repository: `lowcode-project` · Docker image: `lowcode-app`
Drafted 2026-10-21. This is the Week 3 Block A draft, to be refined in the live session on 28 October and then formalised as `docs/specification.md`.

---

## 1 · The application — the 60%

### What it is, in one sentence

A system of record for marketing work requests, in which the approval trail is enforced by the database rather than documented in a policy.

### Who uses it

| Role | Who | May do |
|---|---|---|
| `requester` | Sales rep, founder, product | Open requests, view their own, cancel their own |
| `owner` | Marketing specialist | Own a request, add and complete tasks, send to review |
| `reviewer` | Marketing lead, legal, brand | Approve or reject — only if not the requester and not the owner |
| `admin` | Ops | Everything — but bound by the same rule: cannot approve a request they raised or worked on. Whether admins get a logged override for small teams is an **open decision** (`specification.md` §10) |

### The lifecycle

```
submitted → assigned → in_review → approved
                ↑           │
                └───────────┘   (rework)
                            └──→ rejected
any state (except terminal) → cancelled
```

Terminal states: `approved`, `rejected`, `cancelled`.
`assigned → assigned` is legal: that is reassignment to a different owner, and it still writes a transition.

### Entities

`users` · `requests` · `request_transitions` · `tasks` · `review_checks` · `automation_events`

Full DDL in `schema/001_initial.sql` from Week 5. The one invariant that defines the project: **`request_transitions` is append-only**, enforced by SQLite triggers that abort on `UPDATE` and `DELETE`. `requests.status` is a denormalised copy of the latest transition, with a test asserting the two agree.

### Routes

**Auth**
- `GET /login` · `POST /login` · `POST /logout`

**Requests**
- `GET /requests` — my queue: requests I own, plus tasks assigned to me, by due date
- `GET /requests/new` · `POST /requests` — open a request
- `GET /requests/<id>` — detail, with the full transition timeline
- `POST /requests/<id>/assign` — set owner
- `POST /requests/<id>/review` — assigned → in_review
- `POST /requests/<id>/approve` · `POST /requests/<id>/reject` · `POST /requests/<id>/cancel`

**Tasks**
- `POST /requests/<id>/tasks` — add · `POST /tasks/<id>/complete`

**Review checks**
- `POST /requests/<id>/checks/<key>` — mark a check passed

**Machine interface**
- `POST /api/events` — automation intake. HMAC-signed, idempotent on `(source, external_id)`
- `GET /api/metrics` — aggregates derived from `request_transitions`

Fourteen routes. That is the whole surface.

### The three invariants worth testing

1. A request cannot enter `in_review` while it has an incomplete task.
2. `in_review → approved` is refused while any required check for that request type is unpassed.
3. Nobody approves their own request, and the owner who did the work does not approve it either.

### Explicitly out of scope

State these in the specification. Anything not listed as in scope is out, and these in particular:

- No Gantt charts, dependencies, sprints or estimates
- No time tracking or capacity planning
- No chat or threaded comments — a note on a transition is the whole comment model
- No file attachments
- No multi-tenancy: one team, one database
- No email notifications from the app itself — that is the automations' job
- No auto-assignment or routing logic beyond a default owner per request type
- No mobile app, no public API beyond the two machine routes above

---

## 2 · The portfolio — the 40%

Four automations, each documented as `docs/portfolio/automation-0N.md` with: the business problem (who does it, how often, how long it takes), an architecture diagram, the tools and trigger type, the verbatim prompts, screenshots of it running, and honest answers to the three failure questions.

**Built in Make** (recommended by the course: free tier allows multi-step scenarios and 1,000 operations; Zapier's free tier caps at two steps).

**The boundary that applies to all four:** they talk to the application only through its API — `POST /api/events` for the two that create work, `GET /api/metrics` for the two that report. None of them touches the database directly. From layer 38 of the influence model — *do not let a recommendation silently become an unrestricted write action.*

### Automation 1 — Paid media lead intake · Week 4

**The manual process:** lead-form leads arrive by email or CSV; someone reads them, decides which matter, and creates a follow-up task by hand. Hours of latency on leads whose value decays in minutes.

**The automation:** lead form → Make → filter on qualifying fields → `POST /api/events` with `source: paid_media`, `external_id` = the platform's lead id → the app opens a request of type `lead`, status `submitted`.

**Why idempotency matters here:** ad platforms retry deliveries. `UNIQUE (source, external_id)` means a redelivery is a no-op instead of a duplicate request.

### Automation 2 — Daily open-request digest · Week 5

**The manual process:** someone opens the tracker each morning, works out what is outstanding and who is sitting on it, and chases by hand.

**The automation:** scheduled Make scenario → `GET /api/metrics` → formats open requests by owner and age → email or Slack.

This is the one the brief requires to read or write the database.

### Automation 3 — Performance threshold alert · Week 7

**The manual process:** checking campaign exports for cost or conversion drift, then raising it with whoever owns the campaign.

**The automation:** scheduled → reads a campaign export → compares against thresholds → on breach only, `POST /api/events` with `source: performance`, `external_id` = `"{metric}:{date}"`.

**The rule that makes it useful rather than noisy:** one alert per metric per day, and if an open request already exists for that metric it appends a *task* rather than opening a second request.

### Automation 4 — Weekly audit summary · Week 11

**The manual process:** writing a weekly status update by hand from memory and a spreadsheet.

**The automation:** reads seven days of `request_transitions` → aggregates **in SQL first** (throughput, median cycle time per stage, rejection rate, requests stuck beyond N days) → passes only the aggregates to an LLM for narrative → posts the report.

**Never paste raw log rows into the prompt.** Request titles are user input, which makes them a prompt-injection vector. This reasoning belongs in the Week 11 governance document.

---

## 3 · What lands in the repository, week by week

| Week | Date | What is committed |
|---|---|---|
| 1 ✅ | 14 Oct | `app.py` · `requirements.txt` · `.gitignore` · `README.md` with the project note |
| 2 | 21 Oct | `/contact` with server-side validation · `experiments/week02/` raw outputs · `docs/week02-tool-comparison.md` |
| 3 | 28 Oct | `docs/specification.md` · multi-file app generated from it, on a branch, merged via PR · `docs/week03-review.md` · clean-clone fixes |
| 4 | 4 Nov | `POST /hooks/signup` handler with validation · `docs/portfolio/automation-01.md` · `docs/portfolio/img/` |
| 5 | 11 Nov | `schema/001_initial.sql` · `docs/data-model.md` with ER diagram and the delete rule · CRUD with parameterised queries · string-formatted SQL removed · `automation-02.md` begun |
| 6 | 18 Nov | Templates: responsive, accessible, Tailwind · `docs/week06-ui-review.md` · before/after screenshots |
| 7 | 25 Nov | `ruff.toml` · `tests/` with 8+ tests · `docs/week07-bugs.md` · `automation-03.md` |
| 8 | 2 Dec | `security/` scan evidence · `docs/security-report.md` with before/after table · dependencies pinned |
| 9 | 9 Dec | `Dockerfile` multi-stage, non-root, under 250 MB · `.dockerignore` · `docker-compose.yml` with Postgres |
| 10 | 16 Dec | `docs/deployment.md` including teardown · live HTTPS URL in `README.md` |
| 11 | 6 Jan | `docs/governance.md`, seven sections · `automation-04.md` · **project submitted** |
| 12 | 13 Jan | Presentation · 500-word reflection · two peer reviews · **portfolio submitted** |

---

## 4 · Decisions still owed

1. **The approval deadlock.** The owner who did the work cannot approve it. In a three-person team that can leave nobody eligible. Resolve as an admin override that logs loudly, or drop the rule — and write the reasoning into the governance document either way.
2. **The delete rule.** Week 5 requires this to be decided by hand, on paper, not by an AI. What happens to a request's tasks when the request is deleted — and note that nothing is ever actually deleted here, so the honest answer may be that the question does not arise.
3. **The review checklist.** Replace the placeholder `check_key` values with the real review criteria from layer 39 of the AI-Era Digital Marketing Influence Model: approved claims and evidence, brand consistency and disclosure, permitted data use, audience eligibility.
4. **The problem statement.** The 150 words in the README must describe something actually lived. Week 12 asks what is in the repository that could not be explained in an interview.
5. **An industry problem.** Whether this attaches to a real company's process, via the Industry Engagement Forum. Ask on the Week 3 forum post.
