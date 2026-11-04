# Product definition v2 — a growth consultancy tool for online stores

**Status:** agreed on 30 October 2026, refined on 31 October with the complete
set of 72 action plans; documentation only — nothing below is built yet. This
page explains the product; the technical detail — tables, formulas, routes,
tests — is in [`specification-v2.md`](specification-v2.md). Both supersede
earlier documents wherever they disagree; the v1 design in
[`specification.md`](specification.md) is kept as the record.

## In one sentence

> An app for a marketing agency whose team advises several online stores and
> builds growth systems for them — marketing, growth, automations and AI
> agents — judged on real return, not on ROAS.

**Growth is the method, ROI is the scoreboard.** Every initiative, whatever its
discipline, goes through the same growth loop and is judged on contribution
after all its costs.

## Who uses it

| Who | Signs in? | What they do |
|---|---|---|
| **Consultant** | yes | Works on the clients assigned to them: diagnoses, proposes actions, runs pilots, records results |
| **Lead** | yes | Reviews and approves actions, certifies results — never on work they proposed or own |
| **Admin** | yes | Sets up clients, users and assignments |
| **Service account** | no | One per automation; writes only through the signed API |
| **Client store** | **no** | The stores are the agency's clients; they have no login in the MVP |

**Client stores are fictional, with contrasting profiles**, so the same action
can be shown paying off in one store and losing money in another. Planned for
the demo: three stores — for example a homeware store (average order about €65,
occasional purchases), a natural-cosmetics subscription (about €30, monthly
repeat) and a furniture store (about €600, rare purchases).

**The user group.** The structure — an agency team managing several online
stores — is a real way marketing work is organised; the agency, its people,
the stores and their figures are invented
([`design/user-group.md`](design/user-group.md)). Real-user evidence and the
lecturer's agreement remain open ([§ Open decisions](#open-decisions)).

## The growth loop — the same for every initiative

1. **Diagnose** the client's figures and profile.
2. **Propose** an action for *that* store, usually from one of the 72 ROI Action
   Plans used as a template.
3. **Prioritise:** expected contribution, cost and evidence, compared before
   choosing (as in plan 38).
4. **Approve:** a lead who neither proposed nor owns the action.
5. **Measure** the result from the store's own data, in contribution euros.
6. **Decide** at the end of the measurement window.
7. **Report** to the client.

## Two kinds of thing the agency builds

| | **Action** | **Growth-system component** |
|---|---|---|
| What it is | A bounded pilot or test: a free-shipping threshold for 42 days | Something that keeps running: an abandoned-cart flow, an AI agent, a campaign programme |
| Cost | Setup (one-off) plus operating cost for the pilot period | Operating cost every month: tools, AI usage, media, maintenance |
| Result | Measured once, at the end of its window: net benefit after **all** costs, against a hurdle | Measured **every month**: monthly benefit against monthly operating cost — setup is already spent and not counted again |
| Decision | Adopt, revise, reject or inconclusive | Keep, improve or retire |

**What counts as a benefit** (from the action plans): extra contribution measured
from the store's orders, or paid spending that genuinely falls. Work that others
depend on — data, tracking, reliability — is an *enabler*, shown at cost only.
Freed staff hours are capacity, never money. Each benefit is counted once, even
when several components contribute to it.

**Nothing joins a client's growth system without passing the loop first.** A
new automation, agent or campaign starts as an action; if it is adopted, it
becomes a running component of that client's growth system. A client's
**growth system** is the set of its running components.

**Disciplines are labels, not sections:** ecommerce, digital marketing,
performance marketing, digital growth, agentic AI, automations. Digital growth
is also the loop itself — every action follows it — and as a label it marks
growth initiatives such as retention or referral.

## The central screen: one client's growth system

At the top, the store's **Growth P&L**: sessions × conversion × average order
gives net revenue; minus refunds, product, shipping and payment costs gives
contribution before marketing; minus ad spend, contribution after marketing. It
shows the store's health — it is not the agency's result, which is only ever
the measured, incremental benefit of its work. A missing cost is shown as
*incomplete*, never as zero.

The main view follows the story *diagnose → levers → proof → growth*: the
Growth P&L, then **where to grow** (each metric that is weaker than the store's
own previous three months, with the action plans that target it), the
outcome scoreboard, guardrail flags and the running components. The other
metric classes sit in a **Details** tab. Six classes of metric in all, each
with one job — only the outcome decides:

| Class | What it shows | Role |
|---|---|---|
| **Outcome** (the scoreboard) | Monthly investment in the system, incremental contribution, net gain, system ROI against the client's target, and ROI by month | The verdict |
| **Drivers** | Revenue, orders, conversion rate, average order value, repeat-purchase rate — for the whole store | The context: is the business growing? |
| **Efficiency** | Cost per new customer (CAC) and per order (CPA), by channel | What the result costs |
| **Diagnostics** | ROAS and other platform figures | Kept apart, labelled diagnostic; never decide anything |
| **Guardrails** | Contribution margin and refund rate, checked on every action | Flagged when they worsen beyond a stated tolerance, even if ROI looks good |
| **Quality and risk** | Rejected intake rows, failed automation and agent runs, open alerts | Is the system itself working? |

Each running **component** shows its discipline, lifecycle stage, monthly
cost, contribution, ROI and status (keep, review due, pilot) — where the
consultant acts — and the Details tab has a view **by lifecycle stage**
(acquisition, activation, conversion, engagement, retention, repeat,
expansion, referral, reactivation, and operations for work with no customer
stage), showing where the client's growth system is strong or weak.

The other screens: the **client portfolio** (every assigned client with its
profile and ROI against target), the **review queue** (actions waiting for this
lead), the **action** (plan, approval, history, result) and the **component**
(month-by-month record).

## Where the numbers come from: fictional shop data

The app does not run a shop. A script **generates realistic data for each
fictional store** — months of orders, daily sessions and ad spend by channel —
and the app calculates every result from that data rather than having anyone
type it in.

| Data | Fields the action plans show are needed |
|---|---|
| Orders | date, net revenue, product cost, discount, shipping cost, payment fee, channel, new or returning customer, a **pseudonymous customer code** (no names or contact details); refunds as separate rows. Which customers are in a test's control or test group is kept separately, so customers who never buy still count |
| Sessions | date, channel, sessions |
| Ad spend | date, channel, spend |

- **Contribution** = net revenue − product cost − shipping − payment fees −
  refunds + product cost recovered from returned stock. Discounts are already
  inside net revenue and are never subtracted twice.
- An action's **result** compares its measurement window with a control group
  when the data has one (`holdout`), otherwise with the period before
  (`before_after`) — and says which.
- **Honesty rule:** the effects are written into the data by the generator. The
  demo proves the app *measures correctly*; it does not prove that any tactic
  works. Noise, seasonality and failing actions are included on purpose.
- **Built to change source:** the app reads the same tables whoever fills them.
  Today the generator; from Week 5 a Make automation loading new days from a
  Google Sheet; later, if there is time, exports or a Shopify development store.

## The 72 ROI Action Plans

My own series (Google Drive, *ROI Unified System — 6 disciplines*, all 72
written by 31 October, 12 per discipline), generated with an AI assistant. In v2
they are **templates, requirements and a read-only reference**:

- they define what the fictional data must contain (plan 03, for example,
  measures contribution per assigned visitor with a control group and a
  post-promotion period);
- all 72 are loaded as reference, each tagged with the metric it moves
  ([`plan-lever-map.md`](plan-lever-map.md)), so "where to grow" can point at
  any of them;
- **six plans, one per discipline** (03, 20, 30, 43, 50, 65), are featured and
  are the only ones that can start an action in the MVP;
- plan 38 (experiment prioritisation) shapes the prioritisation step, and plan
  50 (analytics agents) the read-only AI client report.

## Data model for the MVP

Eighteen tables; fields, constraints and formulas are in
[`specification-v2.md`](specification-v2.md).

| Tables | Hold |
|---|---|
| `users`, `user_roles`, `client_assignments` | people, their roles, and which clients each one works on — the basis of "you see only your clients" |
| `clients`, `plan_templates`, `plan_template_tags` | the store profiles, each with its business model (DTC, B2C, B2B, marketplace, subscription or omnichannel), the action-plan templates, and what each plan moves and which stores it suits |
| `actions`, `action_history`, `assignments` | the pilots — benefit type, expected benefit, setup and operating costs, hurdle, comparison, window and post-period, named reviewer, measured result, confidence, decision — their append-only history, and which customers are in each holdout's test or control group, buyers or not |
| `components`, `component_months` | a client's running growth-system components, how each one's benefit is measured, and their append-only monthly cost and benefit |
| `client_reports` | the monthly report drafts and what was sent |
| `orders`, `refunds`, `sessions`, `ad_spend` | the fictional shop data, per client |
| `automation_events`, `outbound_events` | what automations write in, and the outbox of announcements to Make |

Kept from v1: the approval rules in `lifecycle.py`, the formulas in `roi.py`,
the append-only history with database triggers, and Werkzeug scrypt passwords.

## Rules carried over

- The reviewer is never the requester or the owner, checked by identity; admin
  is no exception; with no eligible reviewer an action stays blocked.
- **A consultant sees only their assigned clients** — enforced on every query,
  not by hiding links. This is the main thing the Week 8 security audit should
  test.
- The app never counts saved hours as money, never treats ROAS or attributed
  revenue as a result, never adds ROI percentages together, and never shows a
  result as more certain than its evidence.
- Automations and AI never decide: they read, notify and draft; people approve.
  An AI agent never calculates ROI or forecasts results — the code does, and the
  agent may only explain those figures. The AI client report is sent only after
  a person approves, corrects or rejects it, and carries an "AI-assisted" label.
- Every pilot names one primary metric and its guardrails before it starts, and
  cannot be closed early because the numbers look good.
- A shop-data batch that does not match its control totals is rejected whole.

## Automations (the 40% portfolio)

| Brief type | Automation | Week |
|---|---|---|
| Event-triggered | A store owner emails the agency asking for help: an instant reply introduces the team, links to a booking page for the onboarding call and lists what to prepare; the team is told to follow up (re-mapped 4 November) | 4 |
| Scheduled | Daily intake of new fictional orders, sessions and spend from a Google Sheet, through the signed API | 5 |
| Human approval | A submitted action is routed to its named lead, who decides **in the app** | 7 |
| Scheduled, AI | A read-only monthly client report drafted from the dashboard figures, reviewed before sending (design from plan 50) | 8–11 |

## Against the brief's six minimum requirements

| Requirement | v2 answer |
|---|---|
| ≥ 3 related tables | Eighteen, linked through clients, actions and components |
| ≥ 3 automations, one scheduled, one event-triggered, one with human approval | The four above; a below-target alert stays optional |
| ≥ 2 roles enforced on the data | Consultant, lead and admin; client isolation and reviewer independence on every query |
| DFD, STRIDE, GDPR | To revise for v2; GDPR becomes simpler — the fictional orders hold no customer names or contact details; the personal data is the team's and, through the inquiry reply, prospects' names, addresses and messages |

## Out of scope for the MVP

Client logins or a client portal · live connections to Shopify, GA4 or ad
platforms inside the app · loading all 72 plans or the 179 influence-model
layers · autonomous AI actions · marketing-mix models, LTV or NPV forecasting ·
real customer data · payments · incremental ROAS, a customer data platform or
data warehouse, headless commerce, and agents that move budgets or prices.

## Open decisions

1. **Real users and the lecturer's agreement** to the v2 direction.

Settled in [`specification-v2.md`](specification-v2.md): €35/hour as the
default, *inconclusive* alongside adopt / revise / reject, a hurdle per action
as well as a target per client, and the delete rule (nothing is deleted). The
design pack is revised on schedule: ERD and roles in Week 5, DFD and STRIDE in
Week 8, GDPR in Week 11.
