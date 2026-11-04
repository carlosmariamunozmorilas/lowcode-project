# Metric templates — what the app evaluates, and the fictional data behind it

**Status:** proposal, 4 November 2026 — branch `docs/metric-templates`. Nothing
here is loaded by the app or produced by the generator yet; the three decisions
at the end say what would change (D1 decided: yes). **Source:** Carlos's
*Unified ROI System — variables, KPIs, levers and objects* (A4 summary, 3 pages,
4 November 2026), read in full and kept in the repository:
[`sources/Unified_ROI_Variables_A4_EN.pdf`](sources/Unified_ROI_Variables_A4_EN.pdf).
The machine-readable twin is
[`data/metric_templates.json`](../data/metric_templates.json). **Both files are
generated** by [`scripts/build_metric_templates.py`](../scripts/build_metric_templates.py),
which also checks the catalogue against the app — edit the script, not the
files; `--check` reports a file that is out of date.

## Why this page exists

The app already measures ROI with 13 metrics (spec v2 §4). The Unified ROI
summary lists several hundred variables across six disciplines and three shared
layers, for B2B and B2C. This page selects from it — as its own page 2 says,
*"Select variables for the business model"* — the metrics an agency advising
three fictional online stores needs to evaluate a project, groups them into one
evaluation template per discipline, and states what fictional data each one
needs.

**The selection rule is the ecommerce test.** A variable becomes a metric
template only if (1) it moves or explains a store KPI or an order's economics,
(2) a small ecommerce team can act on it, and (3) the store's own data — orders,
refunds, sessions, ad spend, messages, the app's own records — can show it.
Everything else is listed under [Left out](#left-out-from-the-pdf), with the
reason.

**Result:** 65 metric templates — 28 the app computes today,
18 whose data already exists (a formula in `measure.py` is
all they need — contribution after media also needs decision D1), and
19 that need one of six small fictional data extensions
(E1–E6). **Only a core set of 22 is meant for the screens and the
presentation** — [the core set](#the-core-set); the rest is reference.

## How the PDF maps onto the app

| PDF block | Where it lives in the app |
|---|---|
| 01 Ecommerce | Store drivers, the Growth P&L and funnel diagnostics — the ecommerce template |
| 02 Digital marketing and CRM | Channel sessions, new customers, message metrics — the digital marketing template |
| 03 Digital growth | The growth loop itself (every action) and cohort metrics — the digital growth template |
| 04 Performance marketing | Spend, CPA, CAC; ROAS and MER as diagnostics — the performance template |
| 05 Agentic AI | Agent components and the client report; *Control* is the Week 11 agent checklist |
| 06 Automations | Automation components and intake events; *Reliability* is built as API controls |
| T1 Economics and business | [`roi.py`](../roi.py) and [`measure.py`](../measure.py): contribution, net benefit, ROI |
| T2 Context, data and stack | The client profile, the shop-data tables, this template format (the PDF's *KPI contract*), the quality metrics |
| T3 People, delivery and governance | Users and roles, the approval workflow, `action_history`, the Week 11 policy |

The PDF's **Experiments** record (03) is already the `actions` table: ID → `id`;
objective and hypothesis → `hypothesis`; owner → `owner_id`; funnel stage →
`lifecycle_stage`; audience, control, variants and split → `assignments`;
primary / secondary / guardrail KPI → `primary_metric` plus the two fixed
guardrails; start and end → `window_start`, `window_end`, `post_period_days`;
lift and incremental value → `measured_benefit_eur`; uncertainty →
`confidence`; cost → setup and operating cost and hours; decision → `decision`;
learning → `decision_note`.

## The ROI formula is already the same

The PDF (page 1): *ROI = (incremental contribution before programme costs +
verified savings − programme costs) / programme costs.* Term by term:

| PDF | App (spec v2 §4) |
|---|---|
| Incremental contribution | `measured_benefit_eur` of a `contribution` action — holdout or before/after |
| Verified savings | `measured_benefit_eur` of an `avoided_cost` action — invoice, `documented`, with an evidence note |
| Programme costs | setup cost + operating cost + (setup hours + operating hours) × the client's hourly rate |
| Same period and currency | Euros; the measurement period is the window plus the post-period |
| Count each saving and cost once | `benefit_key`, enforced by a partial unique index |
| ROAS and MER are not ROI | ROAS and MER are diagnostics |
| Released capacity is value only when used or saved | `hours_freed` is capacity, never money — see [differences](#where-the-pdf-and-the-app-differ) |

One difference in practice: an action carries one benefit type, so a project
that both wins contribution and saves a paid cost is recorded as two actions or
components, each evidenced its own way; system ROI then adds them. **One gap:**
for an action that changes media spend, the incremental contribution must be
measured *after media*, and today it is not — see **D1**.

## The template format

From the PDF's *KPI contract* (T2), trimmed to what the app uses. Each metric in
the JSON has: `key` · `name` · `discipline` (its home in the PDF) · `class` (the
spec's six) · `definition` · `formula` · `unit` · `better` (higher, lower or
neither) · `grain` · `source` (tables and fields) · `status` · `extension` ·
`primary` · `plans` (the action plans that move it or decide on it) · `pdf`
(where it comes from) · `note` · `fits` (purchase frequencies it suits, when not
all).

Dropped from the KPI contract: **owner** (an action's owner is enough),
**target** (the only target is the client's ROI target — the app never compares
a store with an invented benchmark), **attribution model and window** (results
come from holdout or before/after, never from attribution), **frequency** and
**currency** (always monthly or the action's period; always euros).

**Status:** built · *ready* — data exists, formula to add · *E1–E6* — needs that
data extension. **⁺** marks a metric *proposed* as a primary metric under D3;
the 13 metrics of today's vocabulary (`lifecycle.METRICS`) keep their place.

## The six evaluation templates

Every template is judged the same way: the **outcome** decides (net benefit
against the hurdle and ROI for a pilot; system ROI and setup payback once
adopted), the store's **Growth P&L** is context and never the result, and every
action is checked on the same **two guardrails**, margin % and refund rate.
What changes by discipline is the primary metric, the drivers that explain the
result, and the diagnostics that help find causes.

### Ecommerce

*Does the store turn its visits into profitable orders?*

- **Decides on:** Incremental contribution
- **Comparison:** holdout per visitor or customer where a group can be assigned; otherwise before/after
- **Featured plan:** 03 Discounts
- **Primary metric options:** Conversion rate, Average order value, Contribution per session *(ready)* ⁺, Add-to-cart rate *(E1)* ⁺, Checkout completion rate *(E1)* ⁺, Mobile conversion rate *(E1)* ⁺, Units per order *(E4)* ⁺, Cost to serve per order *(ready)* ⁺, Contribution margin %, Refund rate
- **Store fit:** All three stores. Roble's few orders (about 36 a week at 0.6%) need a longer window than Luna's or Brote's before any result means anything.

| Class | Metrics |
|---|---|
| Driver | Sessions · Conversion rate · Average order value · Contribution per session *(ready)* · Units per order *(E4)* · Mobile conversion rate *(E1)* |
| Efficiency | Cost to serve per order *(ready)* |
| Diagnostic | Add-to-cart rate *(E1)* · Checkout completion rate *(E1)* · Cart abandonment rate *(E1)* · Discount rate *(ready)* · Refund value rate *(ready)* · Avoidable return share *(E5)* |
| Guardrail | Contribution margin % · Refund rate |
| Quality and risk | Orders with a missing cost · Tracking capture rate *(E1)* |

### Digital marketing and CRM

*Does the store earn demand and keep its customers buying, without paying for every visit?*

- **Decides on:** Incremental contribution
- **Comparison:** holdout per assigned contact for CRM; before/after on the organic channel for SEO and content (observational)
- **Featured plan:** 20 Email segmentation
- **Primary metric options:** New customers, Repeat-purchase rate, Sessions, Conversion rate
- **Store fit:** CRM fits Brote (monthly) and Luna (occasional); for Roble (rare purchases) the useful levers are search and content. Owned channels have no media cost: their cost is the action's own setup and hours.

| Class | Metrics |
|---|---|
| Driver | Sessions · New customers · Repeat-purchase rate · Conversion rate |
| Diagnostic | Message click rate *(E3)* · Unsubscribe rate *(E3)* · Message pressure *(E3)* |
| Guardrail | Contribution margin % · Refund rate |
| Quality and risk | Delivery rate *(E3)* |

### Performance marketing

*Does each euro of media buy contribution the store would not have had anyway?*

- **Decides on:** Incremental contribution after media *(ready)* *(D1)*
- **Comparison:** before/after on the action's channel; a matched-region holdout when the plan allows it (plan 36)
- **Featured plan:** 30 Search terms
- **Primary metric options:** Cost per order (CPA), Customer acquisition cost (CAC), Cost per paid session *(ready)* ⁺, Orders, Conversion rate, New customers, Contribution margin %
- **Store fit:** All three stores buy media (8–15% of revenue). Until D1 is decided, the result is measured as plain incremental contribution.

| Class | Metrics |
|---|---|
| Driver | Ad spend · Sessions · Orders · Conversion rate · Average order value |
| Efficiency | Cost per order (CPA) · Customer acquisition cost (CAC) · Cost per paid session *(ready)* · Cost per click (CPC) *(E2)* · Cost per thousand impressions (CPM) *(E2)* |
| Diagnostic | ROAS · Break-even ROAS *(ready)* · Marketing efficiency ratio (MER) *(ready)* · New-customer share *(ready)* · Click-through rate (CTR) *(E2)* |
| Guardrail | Contribution margin % · Refund rate |
| Quality and risk | Platform overcount *(E2)* · Tracking capture rate *(E1)* |

### Digital growth

*Do first-time buyers come back, and do the stages after the first order grow?*

- **Decides on:** Incremental contribution
- **Comparison:** holdout per customer, over the plan's horizon (30–180 days)
- **Featured plan:** 43 Purchase frequency
- **Primary metric options:** Repeat-purchase rate, Second-order rate within 90 days *(ready)* ⁺, Orders per customer (180 days) *(ready)* ⁺, Reactivation rate *(ready)* ⁺, Cohort contribution at 90 days *(ready)* ⁺, New customers
- **Store fit:** Repeat and reactivation fit Luna (occasional) and Brote (monthly). For Roble (rare purchases) growth means new customers and referral, not repeat.

| Class | Metrics |
|---|---|
| Driver | Repeat-purchase rate · Second-order rate within 90 days *(ready)* · Orders per customer (180 days) *(ready)* · Reactivation rate *(ready)* · Cohort contribution at 90 days *(ready)* · New customers |
| Efficiency | 90-day contribution to CAC *(ready)* |
| Diagnostic | Days to second order *(ready)* |
| Guardrail | Contribution margin % · Refund rate |
| Quality and risk | Orders with a missing cost |

### Agentic AI

*Does the agent produce accepted work for less than it costs, with a person reviewing every output?*

- **Decides on:** Verified avoided cost or Incremental contribution
- **Comparison:** invoice for saved paid work (documented); holdout for shopper-facing assistants (plans 54, 55)
- **Featured plan:** 50 Analytics agents
- **Primary metric options:** Verified avoided cost, Conversion rate
- **Store fit:** Any store. Agents never calculate ROI or forecast (spec §4); freed hours are capacity.

| Class | Metrics |
|---|---|
| Efficiency | Cost per accepted output *(E6)* · Cost per report draft |
| Diagnostic | AI cost per output *(E6)* |
| Guardrail | Contribution margin % · Refund rate |
| Quality and risk | Output acceptance rate *(E6)* · Report correction rate · Report rejection rate · Run failure rate *(ready)* · Hours freed (capacity) |

### Automations

*Does the workflow run reliably, and does it save paid cost or win contribution?*

- **Decides on:** Verified avoided cost or Incremental contribution
- **Comparison:** invoice for saved paid work; a kept holdout for customer-facing flows (plan 65)
- **Featured plan:** 65 Cart recovery
- **Primary metric options:** Verified avoided cost, Conversion rate, Repeat-purchase rate
- **Store fit:** Any store; cart recovery needs carts to recover, so it suits Luna and Brote more than Roble.

| Class | Metrics |
|---|---|
| Driver | Conversion rate · Repeat-purchase rate |
| Efficiency | Cost per run *(ready)* |
| Diagnostic | Cart abandonment rate *(E1)* · Message click rate *(E3)* · Unsubscribe rate *(E3)* |
| Guardrail | Contribution margin % · Refund rate |
| Quality and risk | Run failure rate *(ready)* · Exception rate *(E6)* · Intake quality · Duplicate delivery rate *(ready)* · Orders with a missing cost · Hours freed (capacity) · Below-target alerts |

## The core set

Sixty-five metrics are a reference, not a screen. The dashboards and the Week
12 presentation show only the **core set** below — the most representative
three per discipline, plus the verdict and the two guardrails that every
discipline shares (22 in all). Proposed on 4 November after Carlos
asked for *"only the most representative"*; it is defined once in the build
script and marked `core` in the JSON, so changing it is a one-line edit.

| Shown for | Core metrics | Why these |
|---|---|---|
| Shared | ROI (action, full payback) · System ROI (continuation) · Contribution margin % · Refund rate | The verdict and the two guardrails — shown for every discipline. |
| Ecommerce | Conversion rate · Average order value · Contribution per session *(ready)* | How many visits buy, how much they spend, and what each visit earns. |
| Digital marketing and CRM | Sessions · New customers · Message click rate *(E3)* | Earned traffic, new buyers, and whether owned messages are read. |
| Performance marketing | Incremental contribution after media *(ready)* *(D1)* · Customer acquisition cost (CAC) · ROAS | What media really earned (D1), what a new customer costs, and ROAS shown beside them to explain why it is not ROI. |
| Digital growth | Repeat-purchase rate · Second-order rate within 90 days *(ready)* · 90-day contribution to CAC *(ready)* | Whether customers come back, how soon, and whether the first 90 days paid back their acquisition. |
| Agentic AI | Output acceptance rate *(E6)* · Cost per accepted output *(E6)* · Report correction rate | How much agent work a person accepts, what it costs, and how often a person corrects it. |
| Automations | Run failure rate *(ready)* · Cost per run *(ready)* · Intake quality | Whether the workflows run, what a run costs, and whether data arrives intact. |

## Metric catalogue

Grouped by home discipline; the templates above borrow across groups. Plans are
the action-plan numbers ([`plan-lever-map.md`](plan-lever-map.md)); for the 13
vocabulary metrics they come from the plans' own `moves` tags.

### Shared — outcome, Growth P&L and guardrails (PDF T1)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **Incremental contribution** `contribution` | Outcome | holdout: (contribution per assigned test customer − per assigned control customer) × test customers; before/after: contribution in the measurement period − the equal period before. Order contribution = net revenue − product cost − shipping − payment fee − refunds + restocked cost; the discount is never subtracted again. *Store contribution (Growth P&L) is context, never this figure.* | built | all 48 contribution plans |
| **Verified avoided cost** `avoided_cost` | Outcome | paid cost before − paid cost after, from invoices, with an evidence note; confidence documented. *Freed hours are never avoided cost.* | built | 49, 50, 51, 52, 53, 56, 57, 58, 59, 61, 62, 63, 67, 68, 69, 70, 71, 72 |
| **Net benefit** `net_benefit` | Outcome | measured benefit − setup cost − setup hours × hourly rate − operating cost − operating hours × hourly rate. *Adopt only when net benefit ≥ the action's hurdle.* | built | every action |
| **ROI (action, full payback)** `roi` | Outcome | net benefit ÷ (setup cost + setup hours × rate + operating cost + operating hours × rate). *Same formula as the PDF. ROAS and MER are never ROI.* | built | every action |
| **System ROI (continuation)** `system_roi` | Outcome | (Σ monthly benefits − Σ monthly operating costs incl. hours × rate) ÷ Σ monthly operating costs, over running components, each benefit_key once. *Compared with the client's roi_target; setup is not counted again.* | built | — |
| **Setup payback** `setup_payback` | Outcome | cumulative net benefit since each component started ÷ total setup cost | built | — |
| **Store contribution before marketing** `contribution_before_marketing` | Driver | net revenue − refunds − (product cost − restocked cost) − shipping − payment fees. *Store health, never an action's benefit; incomplete when a cost is missing.* | built | — |
| **Store contribution after marketing** `contribution_after_marketing` | Driver | contribution before marketing − ad spend. *Store health, never an action's benefit.* | built | — |
| **Contribution margin %** `margin_pct` | Guardrail | contribution before marketing ÷ (net revenue − refunds) × 100. *Breach: more than 2 points below the previous three months' average.* | built | 02, 03, 11, 26, 46 |
| **Refund rate** `refund_rate` | Guardrail | orders refunded in the period ÷ orders placed in the period × 100. *Breach: more than 1 point above the previous three months' average.* | built | 12, 40 |

### Ecommerce (PDF 01)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **Sessions** `sessions` | Driver | Σ sessions | built | 16, 17, 19, 33 |
| **Orders** `orders` | Driver | count of orders | built | 29 |
| **Net revenue** `revenue` | Driver | Σ net revenue (refunds are their own P&L line) | built | — |
| **Conversion rate** `conversion` | Driver | orders ÷ sessions | built | 01, 02, 04, 05, 06, 07, 13, 14, 15, 18, 23, 34, 35, 54, 55, 64, 65 |
| **Average order value** `average_order_value` | Driver | net revenue ÷ orders | built | 01, 03, 08, 09, 46 |
| **Contribution per session** `contribution_per_session` ⁺ | Driver | contribution before marketing ÷ sessions. *An action's result is still its incremental contribution; this is the store's rate.* | data ready | 01, 02, 03, 04, 05, 06, 08, 09, 13, 14, 15, 18, 23, 34, 46, 54, 55 |
| **Discount rate** `discount_rate` | Diagnostic | Σ discounts ÷ (Σ net revenue + Σ discounts). *A lever, read with margin %; discounts are already inside net revenue.* | data ready | 03 |
| **Cost to serve per order** `cost_to_serve_per_order` ⁺ | Efficiency | (Σ shipping cost + Σ payment fees) ÷ orders | data ready | 11 |
| **Refund value rate** `refund_value_rate` | Diagnostic | Σ refunds recorded in the period ÷ Σ net revenue. *Shown beside the refund-rate guardrail.* | data ready | 12 |
| **Units per order** `units_per_order` ⁺ | Driver | Σ units ÷ orders | needs E4 | 01, 08, 09, 46 |
| **Add-to-cart rate** `add_to_cart_rate` ⁺ | Diagnostic | sessions with an add-to-cart ÷ sessions | needs E1 | 01, 04, 05, 15, 23, 54, 55 |
| **Checkout completion rate** `checkout_completion_rate` ⁺ | Diagnostic | orders ÷ sessions that started checkout | needs E1 | 07 |
| **Cart abandonment rate** `cart_abandonment_rate` ⁺ | Diagnostic | 1 − orders ÷ sessions with an add-to-cart | needs E1 | 07, 65 |
| **Mobile conversion rate** `mobile_conversion` ⁺ | Driver | mobile orders ÷ mobile sessions | needs E1 | 06 |
| **Avoidable return share** `avoidable_return_share` ⁺ | Diagnostic | refunds with reason damaged, wrong item, not as described or late delivery ÷ all refunds | needs E5 | 12, 40 |

### Digital marketing and CRM (PDF 02)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **New customers** `new_customers` | Driver | orders with is_new_customer = 1 | built | 21, 22, 39, 44, 45, 47 |
| **Message click rate** `email_click_rate` | Diagnostic | clicks ÷ delivered. *Engagement only. Email-platform-attributed revenue is never used: the holdout is.* | needs E3 | 20, 21, 64, 65, 66 |
| **Unsubscribe rate** `unsubscribe_rate` | Diagnostic | unsubscribes ÷ delivered. *Watched like a guardrail on message-heavy actions; the two fixed guardrails stay the only ones that flag a breach (decided 2 November).* | needs E3 | 20, 21, 65, 66 |
| **Message pressure** `messages_per_contact` | Diagnostic | Σ delivered in the month ÷ contactable contacts. *Too high drives unsubscribes; too low leaves the list unused.* | needs E3 | 20, 66 |
| **Delivery rate** `delivery_rate` | Quality and risk | delivered ÷ sent | needs E3 | 20, 65, 66 |

### Performance marketing (PDF 04)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **Incremental contribution after media** `contribution_after_media` | Outcome | incremental contribution of the orders in the action's channel − change in that channel's ad spend, over the same periods and comparison. *Not measured today: the app's contribution result ignores ad spend and uses the whole store — see D1.* | data ready, D1 | 24, 26, 27, 28, 29, 30, 31, 32, 33, 35 |
| **Ad spend** `ad_spend` | Driver | Σ spend. *An input, shown so CPA, CAC and MER can be read.* | built | — |
| **Cost per order (CPA)** `cpa` | Efficiency | ad spend ÷ orders (by channel: channel spend ÷ channel orders) | built | 24, 27, 28, 29, 30, 31, 32, 35 |
| **Customer acquisition cost (CAC)** `cac` | Efficiency | ad spend ÷ new customers. *Paid CAC; blended or fully loaded CAC would add agency and tool costs.* | built | 22, 24, 28, 31 |
| **Cost per paid session** `cost_per_session` ⁺ | Efficiency | channel spend ÷ channel sessions. *Stands in for CPC until clicks exist (E2).* | data ready | 27, 29, 30, 33 |
| **Cost per click (CPC)** `cpc` | Efficiency | spend ÷ clicks | needs E2 | 27, 29, 30 |
| **Cost per thousand impressions (CPM)** `cpm` | Efficiency | spend ÷ impressions × 1,000 | needs E2 | 27, 32 |
| **Click-through rate (CTR)** `ctr` | Diagnostic | clicks ÷ impressions. *A creative and feed diagnostic; never a result.* | needs E2 | 27, 32, 33 |
| **ROAS** `roas` | Diagnostic | channel net revenue (store orders) ÷ channel spend. *Never ROI (spec §9: the promotion with ROAS 3.0 had ROI −0.17).* | built | — |
| **Break-even ROAS** `break_even_roas` | Diagnostic | 1 ÷ contribution margin before marketing (as a ratio). *Read beside ROAS: Luna 2.86, Brote 1.67, Roble 4.00 at their profile margins.* | data ready | 24, 26, 28 |
| **Marketing efficiency ratio (MER)** `mer` | Diagnostic | net revenue ÷ total ad spend (cost scope: ad spend only). *MER is not ROI.* | data ready | 24, 28 |
| **New-customer share** `new_customer_share` | Diagnostic | new-customer orders ÷ orders (by channel when scoped). *Plan 31 warns against chasing it: prospecting spend that buys back existing customers is the waste to find.* | data ready | 22, 31 |
| **Platform overcount** `platform_overcount` | Quality and risk | platform-reported purchases ÷ store orders from the channel. *Shows on screen why platform-attributed revenue is never a result.* | needs E2 | 25, 26, 36 |
| **Tracking capture rate** `tracking_capture_rate` | Quality and risk | tagged purchases ÷ store orders. *Plan 25's acceptance criterion is capture ≥ 98%.* | needs E1 | 25, 37 |

### Digital growth (PDF 03)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **Repeat-purchase rate** `repeat_rate` | Driver | customers with two or more orders in the trailing 90 days ÷ customers with one or more | built | 20, 40, 41, 42, 43, 66 |
| **Second-order rate within 90 days** `second_order_rate_90d` ⁺ | Driver | first-time customers of a month who order again within 90 days ÷ first-time customers of that month. *A cohort needs 90 days after its month, so the latest three cohorts show as incomplete.* | data ready | 20, 21, 39, 40, 41, 42, 43, 66 |
| **Orders per customer (180 days)** `orders_per_customer` ⁺ | Driver | orders ÷ distinct customers over the trailing 180 days | data ready | 43 |
| **Days to second order** `days_to_second_order` | Diagnostic | median days between first and second order, for customers with a second order | data ready | 41, 43 |
| **Reactivation rate** `reactivation_rate` ⁺ | Driver | lapsed customers who order in the month ÷ customers lapsed at its start; lapsed = no order for 180 days (occasional stores) or 60 days (monthly stores). *Not used for rare-purchase stores such as Roble.* | data ready | 20, 35 |
| **Cohort contribution at 90 days** `cohort_contribution_d90` ⁺ | Driver | contribution of a first-time customer's orders in the 90 days from the first order, averaged over the cohort. *Realised, never forecast: LTV forecasting stays out of scope (spec §13).* | data ready | 21, 39, 40, 42, 43, 48 |
| **90-day contribution to CAC** `contribution_to_cac_d90` | Efficiency | cohort contribution at 90 days ÷ CAC of the cohort month. *Above 1.0, the first 90 days covered paid acquisition.* | data ready | 22, 24, 28, 31, 44, 48 |

### Agentic AI (PDF 05)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **Output acceptance rate** `output_acceptance_rate` | Quality and risk | outputs accepted ÷ outputs reviewed | needs E6 | 49, 50, 51, 52, 53, 60 |
| **Cost per accepted output** `cost_per_accepted_output` | Efficiency | (operating cost + operating hours × hourly rate) ÷ outputs accepted. *Plan 60's decision metric.* | needs E6 | 49, 50, 52, 53, 60 |
| **AI cost per output** `ai_cost_per_output` | Diagnostic | AI cost ÷ outputs | needs E6 | 60 |
| **Report correction rate** `report_correction_rate` | Quality and risk | sent reports with was_corrected = 1 ÷ sent reports | built | 50 |
| **Report rejection rate** `report_rejection_rate` | Quality and risk | rejected drafts ÷ reviewed drafts | built | 50 |
| **Cost per report draft** `cost_per_report_draft` | Efficiency | Σ generation cost ÷ drafts | built | 50, 60 |

### Automations (PDF 06)

| Metric | Class | Formula | Status | Plans |
|---|---|---|---|---|
| **Run failure rate** `run_failure_rate` | Quality and risk | failed runs ÷ runs. *Runs and failed runs are already shown as counts.* | data ready | 70, 71, 72 |
| **Cost per run** `cost_per_run` | Efficiency | (operating cost + operating hours × hourly rate) ÷ runs | data ready | 61, 69, 72 |
| **Exception rate** `exception_rate` | Quality and risk | exceptions ÷ runs | needs E6 | 61, 70, 71, 72 |
| **Hours freed (capacity)** `hours_freed` | Quality and risk | as recorded on the component month. *Capacity, never money (spec §4) — see 'Where the PDF and the app differ'.* | built | — |
| **Intake quality** `intake_quality` | Quality and risk | accepted ÷ received shop-data batches | built | — |
| **Duplicate delivery rate** `duplicate_event_rate` | Quality and risk | duplicate events ÷ received events. *A duplicate already changes nothing (external_id); this counts how often it happens.* | data ready | — |
| **Orders with a missing cost** `orders_missing_cost` | Quality and risk | count of orders with any cost missing. *Makes the dependent Growth P&L lines incomplete, never zero.* | built | — |
| **Below-target alerts** `open_alerts` | Quality and risk | accepted alert events | built | — |

## Fictional data

Today's tables — `orders`, `refunds`, `sessions`, `ad_spend`, `assignments`,
`component_months`, `client_reports`, `automation_events` — already carry
46 of the 65 metrics. Six extensions
carry the other 19. All six add columns to existing tables,
except E3, which is one new table.

| | In plain words | Adds to the data | Unlocks | Effort | Changes the intake |
|---|---|---|---|---|---|
| **E1** Funnel steps and device | What shoppers did on the site before buying — viewed a product, added to the cart, started checkout — and whether they were on a phone or a computer; plus how many purchases the analytics tag actually recorded. | sessions.device (mobile or desktop), part of the row's key: client · date · channel · device<br>sessions.product_views, add_to_carts, checkouts_started — sessions that reached each step<br>sessions.tracked_purchases — purchases the analytics tag recorded<br>orders.device | `add_to_cart_rate`, `checkout_completion_rate`, `cart_abandonment_rate`, `mobile_conversion`, `tracking_capture_rate` | medium | yes |
| **E2** Ad delivery and platform-reported purchases | How many people saw and clicked each channel's ads, and how many purchases the ad platform claims — always more than the store really received from it. | ad_spend.impressions, clicks<br>ad_spend.platform_purchases, platform_revenue_eur — what the ad platform claims | `cpc`, `cpm`, `ctr`, `platform_overcount` | small | yes |
| **E3** Message sends (email and SMS) | The emails and SMS each store sent — campaigns and automatic flows such as cart recovery — with how many were delivered, clicked and led to an unsubscribe. | new table messages_daily: client · date · channel (email or sms) · stream (a campaign or flow name) · action_id (nullable) · sent · delivered · clicks · unsubscribes · contactable (contacts who could receive the stream that day) | `email_click_rate`, `unsubscribe_rate`, `messages_per_contact`, `delivery_rate` | medium | yes |
| **E4** Units per order | How many items each order contains, so bundles and cross-selling can be judged. | orders.units (≥ 1) | `units_per_order` | small | yes |
| **E5** Refund reasons | Why each refund happened — damaged, wrong item, not as described, late, or the customer changed their mind — so preventable returns can be told apart. | refunds.reason CHECK in (damaged, wrong_item, not_as_described, late_delivery, changed_mind); all but changed_mind count as avoidable | `avoidable_return_share` | small | yes |
| **E6** Agent and automation output counts | For each AI agent and automation, how much work it produced each month, how much of it a person accepted, how often a person had to step in, and what the AI cost. | component_months.outputs, outputs_accepted, exceptions, ai_cost_eur (nullable; automation and agent components only) | `output_acceptance_rate`, `cost_per_accepted_output`, `ai_cost_per_output`, `exception_rate` | small | no |

### Generation settings

These are **settings for the fictional generator, not benchmarks**: the app
never shows them as targets or compares a store with them. Each is chosen so
that the store's existing figures (spec v2 §9) still hold.

**E1 — funnel and device.** Checkout completion and the two device conversions
are derived, so the funnel multiplies back to each store's conversion today.

| Store | Conversion (today) | Mobile share of sessions | Product-view sessions | Add-to-cart sessions | Checkout starts per add-to-cart | Checkout completion (derived) | Desktop / mobile conversion (derived) | Tag capture |
|---|---|---|---|---|---|---|---|---|
| Luna Home | 1.8% | 68.0% | 62.0% | 6.0% | 45.0% | 66.7% | 2.47% / 1.48% | 93.0% |
| Brote Cosmetics | 2.5% | 75.0% | 66.0% | 7.5% | 50.0% | 66.7% | 3.08% / 2.31% | 95.0% |
| Roble Muebles | 0.6% | 55.0% | 55.0% | 2.5% | 40.0% | 60.0% | 0.86% / 0.39% | 90.0% |

**E2 — ad delivery.** Clicks = the channel's paid sessions × 1.15 (some clicks
never land); impressions = clicks ÷ CTR; platform purchases = the store's orders
from the channel × the over-count below; platform revenue = platform purchases ×
the store's average order, with noise.

| Channel | CTR | Platform purchases per store order |
|---|---|---|
| `meta` | 1.1% | 1.35 |
| `google_shopping` | 0.9% | 1.15 |
| `instagram` | 0.8% | 1.40 |
| `google_search` | 5.0% | 1.10 |
| `pinterest` | 0.5% | 1.50 |

**E3 — messages.** Delivery 98.5–99.2% of sent; flow click rates two to three
times the campaign rate; flow unsubscribes 0.10% of delivered; the contactable
list grows about 1.5% a month.

| Store | Contactable contacts | Campaigns | Campaign click rate | Campaign unsubscribe rate | Flows |
|---|---|---|---|---|---|
| Luna Home | 14,000 | 2 a week | 2.2% | 0.25% | welcome; cart recovery (plan 65); post-purchase |
| Brote Cosmetics | 6,500 | 3 a week | 3.2% | 0.20% | welcome; replenishment; plan 20's segmented campaign |
| Roble Muebles | 4,000 | 2 a month | 1.2% | 0.40% | welcome |

**E4 and E5 — units and refund reasons** (break-even ROAS shown for reference:
1 ÷ the profile margin).

| Store | Units per order (mean) | Damaged | Wrong item | Not as described | Late delivery | Changed mind | Avoidable share | Break-even ROAS |
|---|---|---|---|---|---|---|---|---|
| Luna Home | 2.2 | 20% | 8% | 20% | 7% | 45% | 55% | 2.86 |
| Brote Cosmetics | 1.9 | 15% | 10% | 30% | 5% | 40% | 60% | 1.67 |
| Roble Muebles | 1.15 | 35% | 5% | 25% | 20% | 15% | 85% | 4.00 |

**E6 — output counts.** Luna's analytics agent (plan 50): 4 outputs a month (the
weekly report), 3–4 accepted, no exceptions, AI cost = the generation cost of
that month's report drafts. Luna's cart-recovery flow (plan 65): 30–31 daily
runs, outputs = messages sent (E3), 0–3 exceptions, no AI cost.

### Rules that keep the data honest

1. **Funnel steps nest on every row:** orders ≤ checkout starts ≤ add-to-carts ≤
   product views ≤ sessions.
2. **Device conversions average back** to the store's conversion, weighted by
   the mobile share.
3. **Platforms over-count:** platform-reported purchases exceed the store's own
   orders from that channel, so the screen can show why platform revenue is
   never a result.
4. **An action's message stream goes to its test group only:** the stream's
   sends equal its test assignments; the control group receives nothing. When E3
   is built, cart recovery (Luna) and plan 20 (Brote) follow this rule.
5. **One source for each figure:** an agent component's AI cost is the sum of
   its report drafts' generation cost, never a second number.
6. **Fixed seed, Luna first** (spec v2 §9 build order), and every client keeps
   `is_fictional = 1`.

## Left out from the PDF

| PDF variables | Why they are not templates |
|---|---|
| 01 Catalogue and PIM (SKU, variant, taxonomy, GTIN); order and stock (stockout rate, safety stock, inventory turnover, sell-through, forecast error, supplier lead time); feed rejection rate | Needs a SKU and stock model the fictional data does not have; plans 10 and 67 are rated *no* |
| 01 Site search (zero-result rate, autocomplete, filters) | Needs site-search logs |
| 01 Fulfilment SLA and on-time rate; support contacts, resolution time, CSAT/NPS; UGC | No fulfilment or support events; refund reasons (E5) carry the part that touches contribution |
| 01 Payments (authorisation and decline rates, chargebacks, fraud, recovered payments) | No payment events |
| 01 Operations (languages, currencies, tax, duties, marketplace fees, price parity) | One country and one currency per store; plan 47 is rated *no* |
| 02 B2B and lead generation (MQL, SQL, pipeline, win rate, sales cycle) | None of the three stores sells B2B; plans 57, 62 and 63 are rated *no* |
| 02 Channels outside the stores' mix (influencers, affiliates, retail media, CTV, app stores, local and offline) | Not in any store's channel mix; plan 22 stays *partial* |
| 02 Channel quality (share of search, brand vs non-brand demand, AI-referral conversions, sender reputation) | Needs search-console or query data |
| 03 Recurring models (MRR, ARR, net revenue retention, trial-to-paid, dunning) and service or booking models | Brote's subscription is generated as repeat orders, which repeat rate and cohorts already measure; the rest is not ecommerce |
| 03 Test design (minimum detectable effect, power, sample-ratio mismatch, stopping rules) | The app labels evidence (`confidence`) but does not compute significance — worth one honest sentence in the Week 12 presentation, especially for Roble's small samples |
| 04 Reach, frequency, impression share, creative fatigue, conversion lag, offline conversion import | Needs user-level or platform-side data |
| 04 Marketing-mix modelling, response curves, saturation, marginal ROI, iROAS | Excluded by spec v2 §13 |
| 05 Agent specification and control (models, tools, permissions, triggers, traces, evaluation sets, groundedness, prompt-injection resistance) | Governance, not store metrics: the Week 11 agent checklist; reports already store model, prompt version and cost |
| 05 The 20-agent catalogue | Only the read-only report agent is built; plans 49–59 stay reference |
| 06 Reliability controls (webhook signature, idempotency key, retries, timeouts, rate limits, queues, rollback, versions) | Controls, not store metrics: signature checks and idempotency are built into the API and tested (spec v2 §8, §11); retries, timeouts and queues live in the Make scenarios and their portfolio write-ups; rate limits are a Week 8 question. The duplicate rate is the one metric kept |
| T1 Decision context (seasonality, price elasticity, competitor price, concentration, scenarios); working capital, cash conversion cycle | No stock, cash or competitor model |
| T2 Records and systems (CDP, PIM, ERP, OMS, WMS, warehouse), lineage, identity match, consent coverage | CDP and warehouse are excluded by spec v2 §13; consent coverage belongs on the Week 11 GDPR page |
| T3 People, delivery and governance | Already the app's workflow and audit history and the Week 11 policy — structure, not metrics |

## Where the PDF and the app differ

1. **Released capacity.** The PDF (page 3): *"Released capacity becomes
   financial value only when actually used or saved."* The app never turns
   `hours_freed` into money. I kept the app's rule and read the PDF's line
   through it: *saved* means a paid cost fell (an `invoice` result), and *used*
   means the freed time produced its own measured result in another action,
   valued there. The hours themselves are never priced.
2. **Guardrails.** The PDF treats *guardrail* as a type any KPI can have; the
   app has two fixed guardrails (decided 2 November). Unsubscribe rate and
   similar watch-metrics are diagnostics here.
3. **B2B + B2C.** The PDF covers both; the app's three stores are B2C (two
   direct-to-consumer, one subscription), so the B2B variables are left out.
4. **Contribution-LTV.** The PDF lists contribution-LTV; the app has no
   forecasting (spec v2 §13), so the templates use *realised* cohort
   contribution at 90 days and its ratio to CAC.

## Decisions

**D1 — Measure media actions after media, in their channel.** ✅ *Decided 4
November: yes — implemented in its own pull request (schema, `measure.py`,
spec, tests).* Until then, an action's
contribution result ([`measure.py`](../measure.py), `contribution_between` and
`before_after_benefit`) never subtracts ad spend and always compares the whole
store, although spec v2 §4 says before/after is *"for the action's scope"* and
no scope field exists. So for a media action the result is wrong in both
directions: Roble's search-term pilot (plan 30, in progress), whose whole point
is the media it saves, would show that saving as zero, and an action that adds
spend would look better than it is unless the spend were typed in as operating
cost. Ten plans decide on contribution after media (24, 26–33, 35).
*Recommendation:* add a nullable `scope_channel` to `actions`; when it is set,
the before/after result uses that channel's orders and subtracts the change in
that channel's ad spend. Whole-store actions (scope empty) are unchanged. One
spec paragraph, one formula, one test.

**D2 — Which data extensions to build.** ❓ The six extensions, in plain words,
are in the [Fictional data](#fictional-data) table. *Recommendation (revised 4
November, after the course's "judgement over volume" rule):* build **E2, E4 and
E5** — a few columns each — before the Week 5 intake; add **E1** only if time
allows (it changes the sessions key); **park E3 and E6** (a new table, and
monthly counts typed by the team). The core set needs E3 only for its
message click rate and E6 for its two agent metrics, which stay *reference*
until those are built. **Timing:** E1, E2, E4 and E5
change the rows the shop-data intake accepts, and the intake automation
(automation 2 since the 4 November re-map) is built in Week 5 — so decide each
of them before it is built: build it into the intake from the start, or leave
it out, rather than change the intake afterwards. E3 adds a new kind of row.

**D3 — Load the catalogue into the app.** ❓ *Recommendation:* after D2, load
`data/metric_templates.json` as read-only reference (like the plan templates),
let an action's primary metric be any metric marked ⁺, and let *where to grow*
check every driver and efficiency metric whose data exists — so a weak
add-to-cart rate points at plans such as 04, 05 and 23. This is the "suggest levers to
grow" behaviour already asked for, with more metrics to read.
