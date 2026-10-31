# Specification v2 — MarketingOps, a growth consultancy tool for online stores

**Status:** written on 31 October 2026, documentation only — nothing below is
built yet. This is the technical specification the Week 5 schema and later code
are generated from. The product it implements is described in plain terms in
[`product-definition-v2.md`](product-definition-v2.md); the v1 specification
([`specification.md`](specification.md)) is kept as the record of the earlier
design. Where they disagree, this document wins. Open points are marked ❓.

**Sources folded in:** the product definition v2; the 72 ROI Action Plans
(Google Drive, *ROI Unified System — 6 disciplines*, complete on 31 October
2026, generated with an AI assistant), of which plans 03, 26–31, 38, 50, 60, 65
and 72 were read in full and the rest by title; and the rules already in
`lifecycle.py` and `roi.py`.

> **Growth is the method, ROI is the scoreboard.** Every initiative goes through
> the same loop and is judged on contribution, or on paid cost genuinely
> avoided, after all its costs.

---

## 1 · Stack

| Layer | Choice | Version | Arrives |
|---|---|---|---|
| Language | Python | 3.11+ | Week 1 |
| Back end | Flask | 3.1.3, pinned (with Werkzeug 3.1.9) | Week 3 |
| Templating | Jinja2 | 3.1.6 | Week 3 |
| Data | SQLite, standard-library `sqlite3`, raw parameterised SQL, no ORM | file-based | Week 5 |
| Data (prod) | PostgreSQL | 16, in Compose | Week 9 |
| CSS and charts | Tailwind and Chart.js, both via CDN, no build step | | Week 6 |
| Tests and lint | pytest, Ruff | | Week 7 |
| Security | Bandit · Semgrep · pip-audit | | Week 8 |
| Packaging and hosting | Gunicorn, Docker (multi-stage, non-root), AWS Lightsail | | Weeks 9–10 |
| Automations | Make, through the signed API only | | Weeks 4–11 |

Every database connection runs `PRAGMA foreign_keys = ON` — tested on 28 October:
without it, a new connection let a project be deleted and left its rows
orphaned.

## 2 · Components

```
app.py                  Flask factory, blueprints, error pages
config.py               settings from environment (SECRET_KEY, DATABASE_PATH, API secret)
db.py                   connection per request, PRAGMA foreign_keys, init-db command
auth.py                 login, logout, session, role and client-access checks
lifecycle.py            action stage rules and the identity rule for sign-off (exists)
roi.py                  investment, net gain, ROI, break-even (exists; extended)
measure.py              contribution from orders, an action's measured benefit, system and KPI figures
routes/                 clients, actions, components, reports, review, api
templates/              see §7
schema/002_v2.sql       the v2 schema
scripts/generate_shop_data.py   the fictional-data generator (§9)
data/plan_templates.json        the plan templates (§10)
tests/                  see §11
```

## 3 · Entities

Sixteen tables. Money is stored in euros as REAL, rounded only for display;
dates are ISO 8601 text, UTC.

### People and access

**`users`** — `id` PK · `email` UNIQUE NOT NULL · `full_name` NOT NULL ·
`password_hash` TEXT · `is_service` INTEGER NOT NULL DEFAULT 0 · `is_active`
INTEGER NOT NULL DEFAULT 1 · `created_at`.
`CHECK ((is_service = 1 AND password_hash IS NULL) OR (is_service = 0 AND password_hash IS NOT NULL))`
— a person always has a password hash (Werkzeug scrypt, decided 28 October); an
automation account never has one and cannot sign in. This settles the v1
contradiction between "NOT NULL" and password-less service accounts.

**`user_roles`** — `user_id` FK → users · `role` CHECK in (`consultant`, `lead`,
`admin`, `service`) · PK (`user_id`, `role`). Several roles per person (decided
28 October). `service` is never combined with another role.

**`client_assignments`** — `user_id` FK → users · `client_id` FK → clients · PK
(`user_id`, `client_id`). Which consultants and leads work on which client.

### Clients and catalogue

**`clients`** — the store profile.

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | TEXT | NOT NULL, UNIQUE |
| `sector`, `products`, `audience`, `main_channels` | TEXT | NOT NULL |
| `avg_order_value_eur` | REAL | > 0 |
| `contribution_margin` | REAL | > 0 and ≤ 1 — after product cost, discounts, payment fees and fulfilment |
| `purchase_frequency` | TEXT | CHECK in (`rare`, `occasional`, `monthly`) |
| `monthly_budget_eur` | REAL | ≥ 0 |
| `roi_target` | REAL | e.g. 0.20 |
| `hourly_rate_eur` | REAL | ≥ 0, default 35 ❓ (the action plans use 25) |
| `is_fictional` | INTEGER | NOT NULL DEFAULT 1 — shown on screen |
| `created_at` | TEXT | |

**`plan_templates`** — reference data loaded from `data/plan_templates.json`,
never edited in the app. `id` INTEGER PK (the plan number, 1–72) · `discipline`
CHECK in (`ecommerce`, `digital_marketing`, `performance_marketing`,
`digital_growth`, `agentic_ai`, `automations`) · `title` · `summary` ·
`benefit_type` · `default_window_days` · `default_hurdle_eur` · `setup_hours` ·
`store_fit` (which profiles it suits) · `featured` 0/1 · `source_file`.

### The work

**`actions`** — a bounded pilot.

| Field | Type | Constraint |
|---|---|---|
| `id` | INTEGER | PK |
| `client_id` | INTEGER | FK → clients, NOT NULL |
| `plan_template_id` | INTEGER | FK → plan_templates, nullable |
| `discipline` | TEXT | same CHECK as templates — `digital_growth` labels growth initiatives such as retention or referral; growth is also the loop every action follows |
| `title`, `hypothesis` | TEXT | title NOT NULL; hypothesis required before review |
| `benefit_type` | TEXT | CHECK in (`contribution`, `avoided_cost`, `enabler`) — see §4 |
| `expected_benefit_eur` | REAL | required before review, except for `enabler` |
| `setup_cost_eur`, `setup_hours` | REAL | ≥ 0 — one-off |
| `operating_cost_eur`, `operating_hours` | REAL | ≥ 0 — for the pilot period |
| `hurdle_eur` | REAL | the minimum net benefit that justifies adoption; default from the template (often €500) |
| `comparison` | TEXT | CHECK in (`holdout`, `before_after`) — required before review |
| `window_start`, `window_end` | TEXT | required before review; end after start |
| `requester_id`, `owner_id`, `reviewer_id` | INTEGER | FK → users; reviewer neither requester nor owner (`CHECK`) |
| `status` | TEXT | CHECK in (`submitted`, `assigned`, `in_review`, `approved`, `closed`, `rejected`, `cancelled`) |
| `measured_benefit_eur` | REAL | required to close, except for `enabler` |
| `confidence` | TEXT | CHECK in (`holdout`, `before_after`, `correlated`, `documented`) ❓ — `documented` is new: an avoided cost evidenced by invoices |
| `decision` | TEXT | CHECK in (`adopt`, `revise`, `reject`, `inconclusive`) — required to close |
| `benefit_key` | TEXT | the benefit this action claims — see §4 |
| `created_at` | TEXT | |

**`action_history`** — append-only: `id`, `action_id` FK, `from_status`,
`to_status`, `actor_id` FK, `note`, `created_at`. Triggers abort `UPDATE` and
`DELETE`. Every status change and its history row are one transaction.

**`components`** — a running part of a client's growth system. `id` PK ·
`client_id` FK · `origin_action_id` FK → actions (the adopted pilot), nullable
only for seeded history · `name` · `discipline` · `benefit_type` · `status`
CHECK in (`running`, `review_due`, `retired`) · `started_on` · `retired_on` ·
`benefit_key`.

**`component_months`** — append-only monthly record. `id` PK · `component_id` FK
· `month` (`YYYY-MM`) · `operating_cost_eur` · `operating_hours` ·
`measured_benefit_eur` (NULL for an enabler, or when the benefit is recorded
under another component) · `confidence` · `benefit_key` · `supersedes_id` FK →
component_months · `recorded_by` FK → users · `created_at`. Triggers abort
`UPDATE` and `DELETE`; a correction is a new row that supersedes the old one.

**`client_reports`** — `id` PK · `client_id` FK · `month` · `draft_text` (from
automation 4) · `final_text` · `status` CHECK in (`draft`, `sent`) ·
`reviewed_by` FK → users · UNIQUE (`client_id`, `month`).

### Fictional shop data

**`orders`** — `id` PK · `client_id` FK · `external_id` UNIQUE · `ordered_at` ·
`customer_ref` (a pseudonymous code such as `C-01834`; no names, emails or
addresses exist anywhere) · `is_new_customer` 0/1 · `channel` · `net_revenue_eur`
(after discounts, excluding tax) · `discount_eur` (informational; already inside
net revenue) · `product_cost_eur` · `shipping_cost_eur` · `payment_fee_eur` ·
`assignment_group` CHECK in (`none`, `control`, `test`) · `test_action_id` FK →
actions, nullable.

**`refunds`** — `id` PK · `order_id` FK → orders · `external_id` UNIQUE ·
`refunded_at` · `amount_eur` · `restocked_cost_eur` (product cost recovered when
stock returns). The original order is never edited.

**`sessions`** — `client_id` FK · `date` · `channel` · `sessions` · UNIQUE
(`client_id`, `date`, `channel`).

**`ad_spend`** — `client_id` FK · `date` · `channel` · `spend_eur` · UNIQUE
(`client_id`, `date`, `channel`).

### Automations

**`automation_events`** — what the automations write: `id`, `source`,
`client_id`, `external_id`, `payload`, `received_at`, UNIQUE (`source`,
`external_id`). **`outbound_events`** — the outbox of ids-only announcements to
Make, written in the same transaction as the change they announce, as in v1.

## 4 · Measurement and ROI

**Three kinds of benefit** (from plan 60), chosen before any result exists:

| `benefit_type` | What counts | How it is measured |
|---|---|---|
| `contribution` | Extra contribution from the store's orders | Computed by `measure.py` from orders, refunds and the comparison |
| `avoided_cost` | Paid spending that genuinely falls — a cancelled service, a smaller invoice | Recorded by the consultant with evidence; confidence `documented` |
| `enabler` | Work others depend on: data, tracking, reliability | Cost only; never a benefit figure |

**Freed staff hours are capacity, not money**, and never enter a benefit — the
same rule as v1 and every action plan.

**Contribution of one order** = net revenue − product cost − shipping cost −
payment fee − refunds + restocked product cost. Discounts are already inside net
revenue and are **never subtracted again**.

**An action's measured benefit** (`benefit_type = contribution`), over the
window plus the template's post-period:

- `holdout`: (contribution per assigned customer in `test` − contribution per
  assigned customer in `control`) × customers assigned to `test`. Every assigned
  customer counts, including those who bought nothing. Confidence `holdout`.
- `before_after`: contribution in the window − contribution in the equal-length
  period immediately before, for the action's scope. Confidence `before_after`,
  shown as weaker evidence.

**Two economic views, never mixed:**

| View | Formula | Used for |
|---|---|---|
| **Action — full payback** | net benefit = measured benefit − setup cost − setup hours × rate − operating cost − operating hours × rate; ROI = net benefit ÷ total investment | Closing the pilot; the decision is `adopt` only if net benefit ≥ `hurdle_eur` |
| **Component — continuation** | monthly net = monthly benefit − monthly operating cost − operating hours × rate; ROI = monthly net ÷ monthly operating cost | Keep, improve or retire. Setup is already spent and does not count again |

**System ROI for a client and month** = (Σ benefits − Σ operating costs) ÷ Σ
operating costs over its running components, counting **each benefit once**.
**Setup payback** is shown beside it: cumulative net benefit against total
setup cost since each component started.

**Each benefit is counted once.** A `benefit_key` names the outcome a figure
belongs to. Within a client and month, at most one `component_months` row may
carry a `measured_benefit_eur` for a given `benefit_key` — enforced with a
partial unique index. Two components that contribute to the same outcome share
the key; one carries the benefit, the other records cost only.

**Growth KPIs** for the whole store and month: revenue, orders, conversion
(orders ÷ sessions), average order value, and repeat-purchase rate (customers
with two or more orders in the trailing 90 days ÷ customers with one or more).
**ROAS** (channel revenue ÷ channel spend) is shown as a diagnostic and never
decides anything.

**What the app never does:** count saved hours as money; treat ROAS or
platform-attributed revenue as a result; add ROI percentages together; add up
the example ROIs of the action plans; show a result as more certain than its
evidence.

## 5 · Workflow, roles and access

**An action's stages** are v1's (`lifecycle.ALLOWED`):
`submitted → assigned → in_review → approved → closed`, or `rejected` /
`cancelled`.

- **To enter review:** owner, hypothesis, benefit type, expected benefit (unless
  enabler), comparison, measurement window, and a named reviewer who is a lead
  assigned to the client and is neither requester nor owner.
- **To close:** measured benefit (unless enabler), confidence and decision,
  certified by the named reviewer.
- **On `adopt`,** the reviewer is offered "add to the growth system", which
  creates a component linked to the action. Nothing becomes a component any
  other way.

| Role | May |
|---|---|
| `consultant` | Read assigned clients; create and own actions for them; record component months and avoided-cost evidence; edit report drafts |
| `lead` | Everything a consultant may, plus review, approve, reject and close actions they are named on — never ones they requested or own |
| `admin` | Create clients, users, roles and assignments; read all clients; **no** sign-off bypass |
| `service` | Write through the signed API only |

**Client isolation:** every query that reads or writes client data filters on
`client_assignments` for the signed-in user (admin excepted for reading). A
consultant who changes an id in a URL gets `404`, not another client's data.
Enforced in the data-access functions, not by hiding links.

**The identity rule:** nobody approves, rejects or closes an action they
requested or own, whatever their roles; admin is no exception; with no eligible
reviewer the action stays blocked. `lifecycle.User` becomes multi-role
(`roles: frozenset[str]`), and its existing identity checks stay as they are.

## 6 · Routes

| Method | Path | Who | Does |
|---|---|---|---|
| GET/POST | `/login` · POST `/logout` | anyone · signed in | session |
| GET | `/` | signed in | the client portfolio: assigned clients with profile and system ROI against target |
| GET | `/clients/<id>` | assigned | **the growth-system dashboard** (§7) |
| GET | `/clients/<id>/plans` | assigned | plan templates, ordered by fit to this client's profile |
| GET/POST | `/clients/<id>/actions/new` | assigned consultant | new action, optionally from a template |
| GET | `/actions/<id>` | assigned | the action, its history and its measured result |
| POST | `/actions/<id>/assign`, `/review`, `/approve`, `/reject`, `/close`, `/cancel` | per §5 | stage changes through `lifecycle.py` |
| GET | `/review` | lead | actions waiting for this lead |
| GET | `/components/<id>` | assigned | month-by-month record |
| POST | `/components/<id>/months` | assigned consultant | record a month (or a correction) |
| POST | `/components/<id>/status` | named lead | keep, mark for review, or retire |
| GET/POST | `/clients/<id>/reports/<month>` | assigned | review and send the drafted report |
| GET/POST | `/admin/clients`, `/admin/users` | admin | set-up |
| POST | `/api/events` | HMAC signature | automation writes: `shop_data`, `alerts`, `report_draft`; idempotent |
| GET | `/api/metrics` | HMAC signature | aggregates for automations 2–4 — never raw orders |

## 7 · Screens

- **Portfolio** — each assigned client: name, profile (average order, margin,
  frequency, budget), system ROI against its target, and a "fictional" badge.
- **Growth-system dashboard**, one client and month:
  - **Scoreboard:** monthly operating cost, benefit, net, system ROI against
    target, ROI by month, and setup payback;
  - **Growth KPIs:** revenue, orders, conversion, average order, repeat rate;
  - **Diagnostics:** ROAS by channel, labelled diagnostic;
  - **Components:** discipline, monthly cost, benefit, ROI, confidence and
    status, with alerts and pilots in progress.
- **Plans** — templates that fit this client, with a "start an action" button.
- **Action** — the plan, costs, comparison, history, measured result, net
  benefit against the hurdle, and decision.
- **Review queue**, **component** record, **report** draft editor, and admin
  set-up pages.

Every figure on screen states its confidence where it has one; colour is never
the only signal.

## 8 · Automations

As in [`portfolio/portfolio-plan.md`](portfolio/portfolio-plan.md): daily
shop-data intake (scheduled, W4) · below-target alert on `data.loaded` (event,
W5) · approval routing to the named lead (human approval, W7) · monthly client
report drafted by a read-only AI and reviewed before sending (scheduled AI, W8,
written up W11). The application computes every flag and figure; Make only moves
data and messages. Design references in the action plans: 61 and 71 (intake and
validation), 70 (alerts), 69 and 50 (the report), 72 (idempotency, bounded
retries, unknown outcomes held for review).

## 9 · Fictional shop data

`scripts/generate_shop_data.py` writes six months of history (May–October 2026)
for three stores, with a fixed random seed so every run produces the same data
and tests can rely on it.

| Store | Average order | Margin | Frequency | Budget/month | Baseline |
|---|---|---|---|---|---|
| Luna Home (homeware) | €65 | 35% | occasional | €5,000 | ~12,300 sessions/week, 1.8% conversion |
| Brote Cosmetics (skincare subscription) | ~€30 | ~60% | monthly | ~€2,000 | to set ❓ |
| Roble Muebles (furniture) | ~€600 | ~25% | rare | ~€12,000 | to set ❓ |

The generator produces daily sessions and ad spend by channel, orders with
pseudonymous customers and realistic cost fields, refunds, noise, weekly and
seasonal patterns, and **effects written in for a set of past actions** — some
measured with a holdout group, some before/after, and some that fail, such as
Luna Home's promotional campaign (ROAS 3.0, ROI −0.17). It also writes the
matching actions, components and monthly records, so the dashboards have a
history on day one.

**Honesty rule:** the demo proves the app measures correctly, not that any
tactic works. Every fictional client carries `is_fictional = 1`, and the screen
says so.

**Changing the source later** (a Google Sheet from Week 4, exports or a Shopify
development store) changes who fills these tables, not the tables or the
calculations.

## 10 · Plan templates in the MVP

Six featured templates, one per discipline; the other 66 may be loaded as
reference later.

| Plan | Discipline | Typical benefit type | Why it is in the MVP |
|---|---|---|---|
| 03 Discounts | Ecommerce | contribution | Shows why discounts are never subtracted twice |
| 20 Email segmentation | Digital marketing | contribution | Fits the repeat-purchase store — chosen by title, to verify against the full plan ❓ |
| 30 Search terms | Performance marketing | contribution | Media saved and contribution in one result |
| 38 Experiment prioritisation | Digital growth | — | Shapes the planning screen: compare candidates before committing |
| 50 Analytics agents | Agentic AI | avoided_cost | Also the design of the read-only client report |
| 65 Cart recovery | Automations | contribution | The classic running component; per-customer holdout |

## 11 · Tests (Week 7)

Fixtures are small and separate from the generated demo data.

1. Contribution of an order subtracts costs and refunds, adds restocked cost, and never subtracts the discount again
2. Holdout benefit uses every assigned customer, including those who bought nothing
3. Before/after benefit compares equal-length windows and is labelled `before_after`
4. An action's net benefit and ROI include setup and operating costs and hours at the client's rate
5. `adopt` is refused when net benefit is below the hurdle
6. A component's continuation ROI excludes setup cost
7. System ROI counts each `benefit_key` once; a second benefit row for the same key and month is refused
8. An `enabler` never shows a benefit or an ROI figure
9. An `avoided_cost` result requires the `documented` confidence and its evidence note
10. Saved hours never appear in any benefit
11. A requester or owner cannot approve, reject or close their own action, whatever their roles; admin included
12. With no eligible reviewer, an action cannot enter review
13. A consultant requesting another client's dashboard, action or component gets `404` — the IDOR test
14. A consultant cannot assign an action's reviewer from outside the client's assigned leads
15. A form posting `status`, `measured_benefit_eur` or `decision` directly is ignored — the mass-assignment test
16. `action_history` and `component_months` refuse `UPDATE` and `DELETE`
17. A status change and its history row are written together or not at all
18. `POST /api/events` refuses a bad signature; a redelivered `external_id` changes nothing
19. A refund for an unknown order, or a row for an unknown client, is refused
20. `GET /api/metrics` returns aggregates only — no order rows, no customer references
21. A service account cannot sign in or approve anything
22. The generator with the fixed seed produces identical data twice
23. A person without a password hash, or a service account with one, is refused by the schema
24. Every connection has `foreign_keys` on; deleting a client with actions is refused ❓ *(pending the delete rule)*

## 12 · Security surface — what Week 8 should find

1. **Client isolation (IDOR):** can a consultant read or change another client's data by changing an id?
2. **Sign-off independence:** can anyone approve or close their own work through the route, not just the button?
3. **Mass assignment:** can a form set a status, a result or a decision directly?
4. **The forwarded approval link:** does opening it as someone else refuse the decision?
5. **API trust:** signatures, idempotency, unknown clients, oversized batches.
6. **Prompt injection in the report:** only aggregates reach the model, and a person reviews every draft.
7. **Rewriting history:** do the triggers hold, and does any route try an update?

The full STRIDE analysis is revised for v2 in Week 8 ([`design/stride.md`](design/stride.md), still v1).

## 13 · Out of scope

Client logins or a client portal · live connections to Shopify, GA4 or ad
platforms inside the app · loading all 72 plans as active templates in the MVP ·
the 179 influence-model layers · autonomous AI actions · marketing-mix models,
LTV, NPV or forecasting · real customer data · payments · editing plan templates
in the app.

## 14 · Open decisions ❓

1. **People time:** €35/hour (the app's default) or €25/hour (all 72 plans); now a per-client setting, so the choice is the default.
2. **The `documented` confidence label** for invoice-evidenced avoided costs.
3. **The delete rule** for clients and actions — decided on paper, as Week 5 requires.
4. **Baselines for Brote Cosmetics and Roble Muebles**, set when the generator is written.
5. **Real users and the lecturer's agreement** to v2.
6. **The design pack** — ERD and roles for Week 5, DFD and STRIDE for Week 8, GDPR for Week 11.
