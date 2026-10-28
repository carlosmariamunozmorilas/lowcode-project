# The user group — a hypothetical scenario

> ⚠️ **Hypothetical, not validated.** Everything on this page is a fictional
> but realistic design assumption. Luna Home and its agency do not exist, and
> nothing here describes a real employer, client or my own work history. The
> scenario is good enough to design, seed and demonstrate a prototype. It is
> **not evidence from real users**, and it does not meet the brief's
> requirement for "a real problem for a named group of users". That
> requirement is **still outstanding** (spec §10, question 10).

## The business

**Luna Home** is a fictional Spanish ecommerce business selling decorative
lighting, cushions and small home accessories through a **Shopify** store with
its own checkout. Assumed size: about **€750,000** a year in online revenue, six
employees, an average order value of **€65**.

Shopify supplies orders and sales; GA4 supplies sessions and conversion. The
application estimates revenue with its fixed KPI tree, sessions × conversion
rate × average order value, and needs margin and costs on top to say whether
anything was profitable.

A small, equally fictional **digital marketing agency** runs Luna Home's paid
media, reporting and site changes.

## The five people

Five people use or take part in the workflow. Luna Home's other employees handle
fulfilment and customer service and are outside the initial user group.

| Person | Side | What they do today | Role in the app |
|---|---|---|---|
| **Founder** | Client | Sets commercial priorities and the monthly spending limit; approves budget increases and projects above €500, except ones they requested or own (those stay blocked) | `admin` + `reviewer`: sets up the project, manages users, can create actions; named reviewer for the ecommerce manager's requests |
| **Ecommerce manager** | Client | Requests campaigns and website improvements | `requester` + `reviewer`: requests actions; named reviewer for the founder's requests |
| **Account manager** | Agency | Coordinates requests and reporting; prepares the results review | `requester` + `owner`: creates coordinated tasks and owns reporting work |
| **Paid media specialist** | Agency | Runs Google Ads and Meta Ads | `owner` |
| **Freelance designer/developer** | Agency | Produces creative assets and implements approved site changes | `owner` |

**Several roles per person — decided 28 October 2026, not yet built.** The
current design gives each user exactly one role; the scenario needs three
people to hold two. Permissions are the union of a person's roles, and the
approval restriction is applied **by identity**: nobody reviews an action they
requested or own, whatever roles they hold, and `admin` never bypasses it. The
schema, `lifecycle.py`, route checks and tests that this changes are listed in
spec §3 ("Multiple roles per user"); until they are built, the application
supports one role per user.

## How work is tracked today

Requests arrive by email and WhatsApp. The account manager copies them by hand
into a shared spreadsheet. Budgets are discussed on calls, and approvals stay
scattered across message threads. Monthly reports sit separately in Looker
Studio.

The application connects each request to its owner, estimated cost, target
KPI, approval record and actual outcome.

## How success is reported today

The current reports lead with ad spend, attributed revenue, CPA and ROAS. They
do not consistently combine product margin, agency labour and implementation
costs.

The application separates revenue, ROAS and the estimated contribution after
costs, and records the assumptions and data sources behind every estimate. A
before-and-after change is never treated, by itself, as proof that an action
caused the result.

## One illustrative problem

A promotional campaign spends **€1,500** on advertising and reports **€4,500**
of attributed revenue: a **ROAS of 3.0**, which looks good.

Its assumed **contribution margin is 35%**, after product costs, discounts,
payment fees and fulfilment. That leaves **€1,575 of contribution before
marketing costs**. Subtracting €1,500 of advertising and €400 of creative and
agency work gives an **estimated loss of €325**: an ROI of **−0.17** on the
€1,900 invested.

The report looked positive because it led with ROAS. Nobody could easily find
the final approval, or an agreed profitability target.

Against the project's ROI target of **0.20**, the campaign falls short by a
wide margin. Lowering a target never changes an action's result: ROAS 3.0 and
ROI −0.17 stay what they are.

*This is an illustrative calculation on attributed revenue, not a verified
measure of incremental profit. It is a one-off example, not a recurring monthly
loss.*

## What the problem costs

Assume the five people together spend about **three hours a week** chasing
approvals, reconciling requests and rebuilding reports. At the application's
people-time rate of **€35/hour**, that is about **€455 a month**
(3 × €35 × 52 ÷ 12).

## Approval rules

**Decided, 28 October 2026:**

- The existing rule stays: an action's **named reviewer is neither its
  requester nor its owner**, checked by who the person is, not by their roles.
  People who do the work never give final approval to their own proposals, and
  `admin` is no exception.
- The **founder reviews the ecommerce manager's requests**. When the founder
  requests something, the **ecommerce manager reviews it**, provided they are
  not its owner.
- **If no eligible reviewer exists, the action stays blocked.** There is no
  override, and silence never counts as approval.
- One designated approver per approval stage.
- **The named reviewer certifies results** and closes the action, under the
  same identity rule. `admin` status alone never authorises closing. The
  account manager prepares the results analysis but does not certify it.

**Agreed future requirements**, recorded now and built in their planned weeks:

- **Amount-based routing.** Projects above **€500**, and any budget increase,
  need the founder's approval. This is a separate requirement from the monthly
  limit. **If the founder requested or owns such an action, it stays
  blocked**: approving it would break the identity rule, and the ecommerce
  manager cannot stand in for the founder's mandatory approval.
- **Monthly budget.** About **€5,000 a month**, covering advertising, agency
  labour and creative/development work. Budget being available never
  overrides the reviewer rules.
- **Reminder and escalation.** A reminder after **2 business days** without a
  decision; escalation to the founder after **5 business days**. If the founder
  is already the reviewer, the overdue approval is flagged for the admin and
  stays pending. Nothing is ever auto-approved, and escalation never bypasses
  reviewer eligibility.

## The numbers behind the seed data

| Figure | Value | Source |
|---|---|---|
| Sessions | 12,300 a week | assumption |
| Conversion rate | 1.8% | assumption |
| Average order value | €65 | assumption |
| Orders | ≈ 221 a week | 12,300 × 1.8% |
| Annual revenue | ≈ €748,000 | 221.4 orders × €65 × 52 weeks, consistent with "about €750,000" |
| Contribution margin | 35% | assumption; the app labels the result "contribution before marketing costs" |
| People time | €35/hour | the application's existing rate |
| Monthly budget | €5,000 | assumption, ≈ €15,000 a quarter |
| ROI target | 0.20 | assumption: a 20% net return on total marketing costs; a hypothetical business target, not an industry benchmark |

These feed the seed design in [spec §8](../specification.md). The worked example
in spec §6 is a separate test fixture, with its own store, a 40% margin and
actions A–D that the tests depend on; it is not this scenario, and its numbers
are not meant to match.

## What this scenario cannot show

That a real team has this problem, that it would use the application, or that
the time and money figures are right. Only real users can show that; until
then the application is a prototype built on stated assumptions.
