# Plan lever map — what each of the 72 action plans moves

**Status:** 31 October 2026, rechecked 2 November. All 72 ROI Action Plans
have been read in full (Google Drive, *ROI Unified System — 6 disciplines*,
generated with an AI assistant). This page records, for each plan, the lever it
pulls, the metric it moves, the metric that decides it, and whether the app's
fictional shop data can show that movement. It is the source of the `moves`
tags and `data_fit` in `data/plan_templates.json` and of the "where to grow"
panel (spec v2 §3, §4); nothing here is built yet.

## How to read the columns

- **Moves** — the store metric the lever is designed to change, using the
  app's metric vocabulary (spec v2 §4): `orders`, `sessions`, `conversion`,
  `average_order_value`, `new_customers`, `repeat_rate`, `cac`, `cpa`,
  `refund_rate`, `margin_pct`, and `avoided_cost` (the plan saves a paid cost —
  agents and automations). One extra value: `none` (an enabler that moves no
  store metric by itself). A channel in brackets, such as `sessions` (organic),
  narrows the metric to one channel.
- **Decides** — the plan's own primary decision metric. In every plan this is a
  contribution or a paid cost, never the driver: the driver explains, the
  contribution decides — the same rule as the app.
- **Benefit** — `contribution`, `avoided_cost` or `enabler` (spec v2 §4).
- **Stage** — lifecycle stage (spec v2 §3). Plans that serve the business
  rather than a customer step are marked `operations`.
- **Data** — can the app's fictional data (orders with costs, channel,
  new/returning and a pseudonymous customer; refunds; sessions and ad spend by
  channel) show what the lever moves? **Yes** — fully; **Partial** — the result
  can be measured from orders, but the lever's own diagnostic needs data the
  app does not hold (search logs, device, checkout steps, stock, carriers,
  support tickets, email events); **No** — needs data or a business model
  outside the app.

## Ecommerce (01–12)

| # | Plan | Lever | Moves | Decides | Benefit | Stage | Data |
|---|---|---|---|---|---|---|---|
| 01 | Product assortment | Curated category of up to 20 SKUs | `conversion`, `average_order_value` | Contribution per eligible visitor | contribution | conversion | Partial |
| 02 | Pricing | One alternative price for one product | `margin_pct`, `conversion` | Full-basket contribution per eligible visitor | contribution | conversion | Yes |
| 03 | Discounts | Discount policy change | `margin_pct`, `average_order_value` | Contribution per assigned visitor | contribution | conversion | Yes |
| 04 | Product pages | One improved product-page package | `conversion` | Contribution per eligible visitor | contribution | conversion | Partial |
| 05 | Navigation and search | Category hub, filters, query handling | `conversion` | Contribution per eligible visitor | contribution | conversion | Partial |
| 06 | Mobile experience | Three mobile fixes | `conversion` | Contribution per eligible mobile visitor | contribution | conversion | Partial |
| 07 | Checkout | Up to three checkout changes | `conversion` | Contribution per checkout starter | contribution | conversion | Partial |
| 08 | Bundles | One complementary bundle | `average_order_value` | Full-basket contribution per eligible visitor | contribution | expansion | Yes |
| 09 | Upselling and cross-selling | One upgrade and one add-on per anchor | `average_order_value` | Full-basket contribution per eligible visitor | contribution | expansion | Yes |
| 10 | Inventory | Replenishment rules | stockouts, capital (not in app) | Inventory value −10% and stockout days −25% | contribution + avoided_cost | operations | No |
| 11 | Fulfilment | Pick-pack-carrier changes | `margin_pct` | Fulfilment cost per order −10% | avoided_cost | operations | Partial |
| 12 | Returns | Prevent avoidable returns | `refund_rate` | Avoidable returns −20%, return-adjusted contribution held | contribution | operations | Yes |

## Digital marketing (13–24)

| # | Plan | Lever | Moves | Decides | Benefit | Stage | Data |
|---|---|---|---|---|---|---|---|
| 13 | Customer research | Interviews, segment, one tested application | `conversion` | Contribution per eligible visitor | contribution | acquisition | Partial |
| 14 | Positioning | One position applied to a landing page | `conversion` | Contribution per eligible visitor | contribution | acquisition | Partial |
| 15 | Messaging | Promise, benefits, objections on one page | `conversion` | Contribution per eligible visitor | contribution | conversion | Partial |
| 16 | Technical SEO | Fix up to three indexing root causes | `sessions` (organic) | Organic-cohort contribution vs counterfactual | contribution (observational) | acquisition | Partial |
| 17 | Commercial SEO | Improve five commercial pages | `sessions` (organic) | Organic-cohort contribution vs counterfactual | contribution (observational) | acquisition | Partial |
| 18 | Content strategy | Three buying-question answers on a category page | `conversion` | Contribution per eligible visitor | contribution | conversion | Partial |
| 19 | Organic social | Twelve-post pilot | `sessions` (social) | Incremental contribution; ROI ≥ 25% | contribution (often unknown) | acquisition | Partial |
| 20 | Email segmentation | Four groups: lapsed, recent repeat, recent first-time, prospects | `repeat_rate` | Contribution per assigned contact, 14 days | contribution | retention | Yes |
| 21 | Lifecycle marketing | Welcome-to-first-purchase journey | `new_customers` (first purchase) | 30-day contribution per entrant | contribution | activation | Partial |
| 22 | Partnerships and affiliates | Up to two commissioned partners | `new_customers`, `cac` | Incremental net profit after all commissions | contribution | referral | Partial |
| 23 | Trust building | Verified proof module near the buy button | `conversion` | Contribution per eligible visitor, 14 days | contribution | conversion | Partial |
| 24 | Channel allocation | Move up to 10% of flexible budget between channels | `cpa`, `cac` | Net marketing contribution; ROI ≥ 25% | contribution | acquisition | Yes |

## Performance marketing (25–36)

| # | Plan | Lever | Moves | Decides | Benefit | Stage | Data |
|---|---|---|---|---|---|---|---|
| 25 | Conversion tracking | Tested purchase and refund measurement | `none` | Capture ≥ 98%, duplicates ≤ 0.5%, values correct | enabler | operations | Partial |
| 26 | Optimization signals | Contribution values instead of revenue values for bidding | `margin_pct` (paid orders) | Contribution after media | contribution | acquisition | Partial |
| 27 | Campaign structure | Restructured campaigns | `cpa` | Contribution after media | contribution | acquisition | Partial |
| 28 | Budget allocation | Budget moved by marginal contribution | `cpa`, `cac` | Contribution after media | contribution | acquisition | Yes |
| 29 | Bidding | One target change within the existing strategy | `orders` (paid), `cpa` | Contribution after media | contribution | acquisition | Partial |
| 30 | Search terms | Query exclusions | `cpa` | Contribution after media, media saved | contribution | acquisition | Partial |
| 31 | Audience strategy | Exclude recent purchasers from prospecting | `cac`, `cpa` | Contribution after media | contribution | acquisition | Partial |
| 32 | Creative testing | One challenger ad package | `cpa` | Contribution after media and project cost | contribution | acquisition | Partial |
| 33 | Product feeds | Feed repairs and one title policy | `sessions` (shopping) | Contribution after media and project cost | contribution | acquisition | Partial |
| 34 | Landing pages | One module change on a paid-traffic template | `conversion` | Contribution per assigned visitor, 28 days | contribution | conversion | Partial |
| 35 | Remarketing | 7-day vs 30-day recency window | `cpa`, `conversion` | Contribution after media and project cost | contribution | reactivation | Partial |
| 36 | Incrementality testing | Activity on vs withheld in matched regions | any channel | Study-horizon net gain ≥ €500 | contribution | operations | Partial |

## Digital growth (37–48)

| # | Plan | Lever | Moves | Decides | Benefit | Stage | Data |
|---|---|---|---|---|---|---|---|
| 37 | Bottleneck diagnosis | Reconciled funnel and order-economics bridge | `none` (diagnoses all) | One constraint or a repair gate | enabler | operations | Partial |
| 38 | Experiment prioritization | Compare candidates before committing | `none` | Ranked brief | enabler | operations | Yes |
| 39 | Activation | Optional product-fit selector | `new_customers` (first valid order) | Contribution per entrant; net ≥ €500 | contribution | activation | Partial |
| 40 | Onboarding | Product-use guide after purchase | `refund_rate`, `repeat_rate` | Contribution per customer, 45 days | contribution | engagement | Partial |
| 41 | Time to value | Direct link to the purchased product's guide | `repeat_rate` | Contribution per customer, 30 days | contribution | engagement | Partial |
| 42 | Retention | Named case owner for first-order issues | `repeat_rate` | Contribution per customer, 90 days | contribution | retention | Partial |
| 43 | Purchase frequency | Reorder-previous-basket shortcut | `repeat_rate` | Contribution per customer, 180 days | contribution | repeat | Yes |
| 44 | Referral programmes | Capped friend and advocate reward | `new_customers` | Incremental net gain after rewards | contribution | referral | Partial |
| 45 | Growth loops | Shareable product collections | `new_customers` | Incremental net gain; loop ratio | contribution | referral | Partial |
| 46 | Monetization | Optional paid service | `average_order_value`, `margin_pct` | Contribution per shopper, 28 days | contribution | expansion | Partial |
| 47 | Market expansion | One new country | `new_customers` | Full-cost pilot net gain | contribution | acquisition | No |
| 48 | Cohort analysis | Reconciled first-order cohorts at D30/60/90 | `none` (diagnoses retention) | One decision brief or repair | enabler | operations | Yes |

## Agentic AI (49–60)

| # | Plan | Lever | Moves | Decides | Benefit | Stage | Data |
|---|---|---|---|---|---|---|---|
| 49 | Research agents | Read-only public research briefs | `avoided_cost` | Avoided paid research, quality gates | avoided_cost | operations | Yes |
| 50 | Analytics agents | Read-only analytics report | `avoided_cost` | Avoided paid analysis | avoided_cost | operations | Yes |
| 51 | Campaign audit agents | Read-only campaign audits | `avoided_cost` | Avoided audit fees | avoided_cost | operations | Partial |
| 52 | Experiment agents | Experiment protocol drafts | `avoided_cost` | Avoided preparation cost | avoided_cost | operations | Yes |
| 53 | Creative agents | Claim-grounded ad drafts | `avoided_cost` | Avoided copy production | avoided_cost | operations | Partial |
| 54 | Merchandising agents | Reviewed collection ranking | `conversion` | Whole-store contribution per visitor | contribution | conversion | Partial |
| 55 | Shopping assistants | Recommendation-only product finder | `conversion` | Whole-store contribution per visitor | contribution | conversion | Partial |
| 56 | Support agents | Staff-facing support drafts | `avoided_cost` | Avoided paid preparation | avoided_cost | operations | No |
| 57 | Sales research agents | Company-level B2B research | `avoided_cost` | Avoided paid research | avoided_cost | operations | No |
| 58 | Operations agents | Delayed-order investigation packs | `avoided_cost` | Avoided paid investigation | avoided_cost | operations | No |
| 59 | Knowledge access | Permission-aware procedure answers | `avoided_cost` | Avoided specialist hours | avoided_cost | operations | No |
| 60 | Agent economics | Unit economics of agents | `none` | Cost per accepted output | enabler | operations | Yes |

## Automations (61–72)

| # | Plan | Lever | Moves | Decides | Benefit | Stage | Data |
|---|---|---|---|---|---|---|---|
| 61 | System integration | Intake between systems | `avoided_cost` | Avoided paid rekeying | avoided_cost | operations | Yes |
| 62 | Lead capture | Form to deduplicated CRM inquiry | `avoided_cost` | Avoided paid capture | avoided_cost | operations | No |
| 63 | Lead routing | Deterministic advisor assignment | `avoided_cost` | Avoided paid admin | avoided_cost | operations | No |
| 64 | Follow-up triggers | Two opted-in emails after an inquiry | `conversion` | Contribution per assigned person, 30 days | contribution | conversion | No |
| 65 | Cart recovery | Cart-abandonment email flow | `conversion` | Contribution per customer, holdout | contribution | conversion | Partial |
| 66 | Post-purchase journeys | Two opted-in emails after delivery | `repeat_rate` | 90-day post-assignment contribution | contribution | engagement | Partial |
| 67 | Inventory and feed updates | Price and stock sync to the feed | `avoided_cost` | Avoided feed maintenance | avoided_cost | operations | No |
| 68 | Order operations | Draft warehouse preparation packets | `avoided_cost` | Avoided preparation admin | avoided_cost | operations | No |
| 69 | Reporting | Weekly reconciled review pack | `avoided_cost` | Avoided reporting work | avoided_cost | operations | Yes |
| 70 | Exception alerts | Three alert families with ownership | `avoided_cost` | Avoided paid checking | avoided_cost | operations | Yes |
| 71 | Data quality | Layered validation and quarantine | `avoided_cost` | Avoided checking and correction | avoided_cost | operations | Yes |
| 72 | Workflow reliability | Idempotency, bounded retries, recovery | `avoided_cost` | Avoided rework | avoided_cost | operations | Yes |

## What the full reading shows

1. **Every plan is a specific lever for a specific metric.** No plan decides on
   its driver: conversion, average order or repeat rate always explain, and a
   contribution or a paid cost always decides.
2. **Customer stages are uneven.** Acquisition (15 plans) and conversion (15)
   dominate; activation (2), engagement (3), retention (2), repeat (1),
   expansion (3), referral (3) and reactivation (1) are thin. 27 plans serve
   operations rather than a customer stage.
3. **Benefit types:** 48 contribution, 19 avoided paid cost, 5 enablers.
4. **Data fit:** 20 plans fit the app's fictional data fully, 41 partly, 11 not
   at all. The "where to grow" view can only point at metrics the app measures:
   conversion, average order, repeat rate, new customers, CAC, CPA, refund rate,
   margin and sessions by channel.
5. **Plan 20 is verified.** Email segmentation suits a repeat-purchase store.
   Three of its four groups (lapsed, recent repeat, recent first-time) come from
   customer history, which the fictional orders hold. The fourth, prospects who
   have never bought, has no orders: the generator creates them as fictional
   pseudonymous contacts in `assignments` (decided 2 November), standing in for
   an email platform's contact list.
6. **Plans 26, 27, 29 and 31 were reread on 2 November 2026.** 27 was right;
   26 (contribution-value signals change the margin mix of paid orders, not
   CPA), 29 (the worked change relaxes a target to buy useful volume) and 31
   (a recent-purchaser exclusion cuts reacquisition spend; the plan warns
   against chasing a new-customer count) were corrected.
