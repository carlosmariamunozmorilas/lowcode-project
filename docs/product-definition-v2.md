# Product definition v2 — a growth consultancy tool for online stores

**Status:** agreed on 30 October 2026, documentation only — nothing below is
built yet. This page supersedes earlier documents wherever they disagree; the
full v1 design in [`specification.md`](specification.md) stays as the detailed
reference for the parts v2 keeps (the action workflow, the approval rules, the
ROI formulas, the append-only record).

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
| Cost | Mostly one-off | Recurring each month: tools, AI usage, media, maintenance |
| Result | Measured once, at the end of its window | Measured **every month** |
| Decision | Adopt, revise, reject or inconclusive ❓ | Keep, improve or retire |

**Nothing joins a client's growth system without passing the loop first.** A
new automation, agent or campaign starts as an action; if it is adopted, it
becomes a running component of that client's growth system. A client's
**growth system** is the set of its running components.

**Disciplines are labels, not sections:** ecommerce, digital marketing,
performance marketing, automations, agentic AI. Digital growth is not a label
— it is the loop itself.

## The central screen: one client's growth system

| Level | What it shows | Role |
|---|---|---|
| **Scoreboard** | Monthly investment in the system, incremental contribution, net gain, system ROI against the client's target, and ROI by month | The verdict |
| **Growth KPIs** | Revenue, orders, conversion rate, average order value, repeat-purchase rate — for the whole store | The context: is the business growing? |
| **Diagnostics** | ROAS and other platform figures | Kept apart, labelled diagnostic; never decide anything |
| **Components** | Each running component with its discipline, monthly cost, contribution, ROI and status (keep, review due, pilot) | Where the consultant acts |

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
| Orders | date, net revenue, product cost, discount, shipping cost, payment fee, refund, channel, new or returning customer, **assignment group** (control or test) |
| Sessions | date, channel, sessions |
| Ad spend | date, channel, spend |

- **Contribution** = net revenue − product cost − shipping − payment fees −
  refunds. Discounts are already inside net revenue and are never subtracted
  twice.
- An action's **result** compares its measurement window with a control group
  when the data has one (`holdout`), otherwise with the period before
  (`before_after`) — and says which.
- **Honesty rule:** the effects are written into the data by the generator. The
  demo proves the app *measures correctly*; it does not prove that any tactic
  works. Noise, seasonality and failing actions are included on purpose.
- **Built to change source:** the app reads the same tables whoever fills them.
  Today the generator; from Week 4 a Make automation loading new days from a
  Google Sheet; later, if there is time, exports or a Shopify development store.

## The 72 ROI Action Plans

My own series (Google Drive, *ROI Unified System — 6 disciplines*, 50 of 72
written by 30 October), generated with an AI assistant. In v2 they are
**templates and requirements, not a catalogue to load in full**:

- they define what the fictional data must contain (plan 03, for example,
  measures contribution per assigned visitor with a control group and a
  post-promotion period);
- about **six plans, one per discipline**, become action templates for the MVP;
- plan 38 (experiment prioritisation) shapes the prioritisation step, and plan
  50 (analytics agents) the read-only AI client report.

## Data model for the MVP

| Table | Holds |
|---|---|
| `users` | consultants, leads, admins, service accounts |
| `clients` | the store profile: sector, products, average order value, margin, purchase frequency, monthly budget, audience, main channels, ROI target |
| `client_assignments` | which consultant works on which client — the basis of "you see only your clients" |
| `actions` | the pilot: client, discipline, plan template, hypothesis, expected contribution in €, cost in € and hours, measurement window, named reviewer, status, measured result, confidence, decision |
| `action_history` | append-only: every status change, who, when |
| `components` | a client's running growth-system components, each linked to the action it came from |
| `component_months` | append-only monthly cost and contribution per component |
| `orders`, `sessions`, `ad_spend` | the fictional shop data, per client |

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

## Automations (the 40% portfolio)

| Brief type | Automation | Week |
|---|---|---|
| Scheduled | Daily intake of new fictional orders, sessions and spend from a Google Sheet, through the signed API | 4 |
| Event-triggered | When a component's monthly ROI falls below its client's target, or an action's window ends, notify the consultant | 5–7 |
| Human approval | A submitted action is routed to its named lead, who decides **in the app** | 7 |
| Scheduled, AI | A read-only monthly client report drafted from the dashboard figures, reviewed before sending (design from plan 50) | 8–11 |

## Against the brief's six minimum requirements

| Requirement | v2 answer |
|---|---|
| ≥ 3 related tables | Ten, linked through clients, actions and components |
| ≥ 3 automations, one scheduled, one event-triggered, one with human approval | The four above |
| ≥ 2 roles enforced on the data | Consultant, lead and admin; client isolation and reviewer independence on every query |
| DFD, STRIDE, GDPR | To revise for v2; GDPR becomes simpler — the fictional orders hold no customer names or contact details, only staff data is personal |

## Out of scope for the MVP

Client logins or a client portal · live connections to Shopify, GA4 or ad
platforms inside the app · loading all 72 plans or the 179 influence-model
layers · autonomous AI actions · marketing-mix models, LTV or NPV forecasting ·
real customer data · payments.

## Open decisions

1. **People time:** €35/hour (the app) or €25/hour (the action plans).
2. **Closing decisions for actions:** add *inconclusive*, and align with the
   plans' adopt / revise / reject.
3. **A target per action** (each plan sets its own hurdle) as well as a target
   per client.
4. **The delete rule** — decided on paper, as Week 5 requires.
5. **Real users and the lecturer's agreement** to the v2 direction.
6. **Revising the design pack** (ERD, roles, DFD, STRIDE, GDPR) for v2.
