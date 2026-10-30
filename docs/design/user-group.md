# The user group — an agency team and its fictional client stores

> ⚠️ **Real roles, fictional clients — not validated.** The users are the team
> of a marketing agency that advises several online stores: a common, real
> structure of marketing work. The agency, its people and its client stores on
> this page are **invented design assumptions**; nothing here describes a real
> employer, client or company. The scenario is good enough to design, seed and
> demonstrate a prototype. It is **not evidence from real users**, and whether
> it meets the brief's "real problem for a named group of users" is a question
> for the lecturer — that requirement is **still outstanding**.
>
> *Revised on 30 October 2026 for product v2
> ([`../product-definition-v2.md`](../product-definition-v2.md)). The v1
> version described one store, Luna Home, and the five people around it; Luna
> Home remains as one of the fictional clients.*

## The users: an agency team

| Role in the app | Who | What they do |
|---|---|---|
| **Consultant** | Account consultants | Each works on the clients assigned to them: reads the store's figures, proposes actions, runs pilots, prepares results and the client report |
| **Lead** | Senior consultant or head of growth | Approves actions and certifies results — never on work they proposed or own |
| **Admin** | Agency operations | Sets up client stores, users and who works on which client |
| **Service** | One account per automation | Writes only through the signed API; never approves anything |

The client stores are **not users**: they have no login in the MVP. Their
people — a founder, an ecommerce manager — are contacts outside the app; what
they agree to is recorded by the consultant.

**Nobody approves their own work.** An action's named lead is neither the
consultant who proposed it nor the one who owns it, checked by who the person
is, not by their role. If no eligible lead exists, the action stays blocked:
no override, and silence never counts as approval.

## The clients: three fictional online stores

Chosen to contrast, so the same action can be shown paying off in one store and
losing money in another. The figures are planning assumptions for the data
generator, to be finalised when it is built.

| | **Luna Home** | **Brote Cosmetics** | **Roble Muebles** |
|---|---|---|---|
| Activity | Decorative lighting, cushions, home accessories | Natural skincare, with a subscription | Furniture |
| Average order value | €65 | ~€30 | ~€600 |
| Contribution margin | 35% | ~60% | ~25% |
| Purchase frequency | Occasional | Monthly, repeat | Rare |
| Monthly marketing budget | €5,000 | ~€2,000 | ~€12,000 |
| Audience | Home-decor buyers | Eco-conscious skincare buyers | People furnishing a new home |
| Main channels | Meta, Google Shopping | Instagram, email | Google Search, Pinterest |
| ROI target | 0.20 | to set | to set |

**Luna Home's baseline** carries over from v1: about 12,300 sessions a week, a
1.8% conversion rate and a €65 average order — about 221 orders a week and
about €748,000 a year. The other two stores get equivalent baselines when the
generator is designed.

## The problem the agency has today

For each client, someone exports orders, sessions and ad spend from the store
platform, the analytics tool and the ad accounts, and pastes them into a
reporting sheet. Approvals happen in email threads and calls. The monthly
report leads with ad spend, attributed revenue and ROAS, and rarely combines
product margin, agency hours and implementation costs. Nobody can say, for a
given client, which running campaigns, automations and agents are paying for
themselves.

## One illustrative problem

At Luna Home, a promotional campaign spends **€1,500** on advertising and
reports **€4,500** of attributed revenue: a **ROAS of 3.0**, which looks good.
At a **35% contribution margin**, that is **€1,575 of contribution before
marketing costs**. Subtracting €1,500 of advertising and €400 of creative and
agency work gives an **estimated loss of €325**: an ROI of **−0.17** on the
€1,900 invested, below the client's 0.20 target.

*An illustrative calculation on attributed revenue, not a verified measure of
incremental profit.*

## What the problem costs

For one client, assume about **three hours a week** of chasing approvals,
reconciling exports and rebuilding reports. At the application's people-time
rate of **€35/hour** ❓ *(the ROI Action Plans use €25/hour; to decide)*, that
is about **€455 a month** (3 × €35 × 52 ÷ 12). Across several clients, the
agency's figure grows with the client count — an assumption to state, not a
measurement.

## Rules carried over from v1

- The reviewer is never the requester or the owner, checked by identity; admin
  is no exception; with no eligible reviewer an action stays blocked.
- The named lead certifies results; admin status alone never closes an action.
- **A consultant sees only their assigned clients** — new in v2, enforced on
  every query.
- Approval reminders after **2 business days** (automation 3).

**No longer applicable in v2:** the v1 rules built around Luna Home's own staff
— the founder approving projects above €500, and escalation to the founder —
assumed client people with logins. In v2 those decisions sit with the agency's
lead; recording a client's own sign-off is a later option, not part of the MVP.

## What this scenario cannot show

That a real agency has this problem, that it would use the application, or that
the time and money figures are right. Only real users can show that; until
then the application is a prototype built on stated assumptions.
