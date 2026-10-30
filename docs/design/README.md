# Design pack — MarketingOps against the project brief

The *Low-Code/No-Code Project Brief* (Dr Matt Lemon, 24 October 2026) sets six
minimum requirements for every project. This folder holds the evidence for each
one, in the form the brief asks for. The technical detail behind every page is
in [`../specification.md`](../specification.md).

## The project, in the brief's own format

| Project | Users | Core app | Scheduled automation | Triggered automation | Approval step |
|---|---|---|---|---|---|
| **MarketingOps v2** — a growth consultancy tool for online stores | A marketing agency's team — consultants, leads and an admin — advising several online stores; the client stores are fictional, with contrasting profiles ([user group](user-group.md)) ⚠️ | Each client's growth system — every running marketing, growth, automation and AI component — with its ROI against the client's target; new initiatives enter as actions with a prediction and a cost, are approved by an independent lead, and are measured from the store's own data ([product definition v2](../product-definition-v2.md)) | Daily intake of each client's new orders, sessions and ad spend | A client's new data lands and part of its growth system is below target, or a pilot's window has ended: the consultant is told | A named lead approves each action before the work starts, and separately certifies its result |

⚠️ **The users are real roles; the clients are fictional.** The brief asks for
"a real problem for a named group of users", and the Week 4 sheet warns that
contrived scenarios mark badly. The users are an agency team managing several
online stores — a real structure of work — while the stores and their data are
invented, as [user-group.md](user-group.md) explains. That is enough to design,
seed and demonstrate a prototype; it is not evidence from real users or real
stores. Real-user evidence is still outstanding, and whether this scenario is
acceptable is a question for the lecturer.

The application is generated with an AI assistant from a written specification
(the Session 3 method) and the automations are built in **Make**, the course's
low-code platform. It is an own idea rather than one of the twenty listed, so
the brief requires it to be **agreed with the lecturer before building starts**.
The closest listed idea is project 2, IT helpdesk ticketing — the brief's own
worked example — which shares its shape: requests, an owner, a manager's
approval and an audit trail.

## The six minimum requirements

For product v2. The pages for requirements 1, 3, 4, 5 and 6 still describe v1
and are revised in the weeks shown; the v2 answer is summarised here.

| # | Requirement | Minimum | Evidence | Page |
|---|---|---|---|---|
| 1 | Data model | ≥ 3 related tables, PKs and FKs | v2 MVP: 10 tables — clients, assignments, actions, history, growth-system components and their monthly records, users, and the fictional shop data | [`../product-definition-v2.md`](../product-definition-v2.md); [`erd.md`](erd.md) *v1, revised for Week 5* |
| 2 | Automations | ≥ 3: one scheduled, one event-triggered, one with a human approval step | 4: shop-data intake (scheduled) · below-target alert (event) · approval routing (approval) · monthly client report (scheduled, read-only AI) | [`../portfolio/portfolio-plan.md`](../portfolio/portfolio-plan.md) |
| 3 | Role-based access | ≥ 2 roles, enforced on the data | Consultant, lead, admin and service; each consultant sees only their assigned clients, enforced on every query; nobody approves their own work; record tables protected by database triggers | [`roles.md`](roles.md) *v1, revised for Week 5* |
| 4 | Data flow diagram | Level 1, trust boundaries | 7 processes, 2 data stores, 4 external entities, 15 numbered flows, 11 crossing a boundary | [`dfd.md`](dfd.md) |
| 5 | Threat analysis | STRIDE on every boundary-crossing flow | 18 threats, each with a mitigation and the test or week that proves it | [`stride.md`](stride.md) |
| 6 | Data protection | Lawful basis, minimisation, retention, access | Staff names and emails only; no customer data by design; erasure without breaking the audit trail | [`gdpr.md`](gdpr.md) |

## The submission checklist, mapped

| The brief asks for | Where it will be |
|---|---|
| Working app shared with the lecturer, test accounts for each role | Live URL in the root README (Week 10); one seeded account per role, credentials sent privately, never committed |
| ERD | [`erd.md`](erd.md) |
| Role table with where each rule is enforced | [`roles.md`](roles.md) |
| Three or more automations, each with a successful test run | `../portfolio/automation-01.md` … `-04.md`, screenshots in `../portfolio/img/` |
| Level-1 DFD | [`dfd.md`](dfd.md) |
| STRIDE table with the mitigations actually built | [`stride.md`](stride.md) — the *Status* column is updated as each one is built and tested |
| GDPR write-up | [`gdpr.md`](gdpr.md) |
| Short demo video of the main user journey | Week 12: a consultant proposes an action for one client, its named lead approves it, the result is measured from the store's data, and the client's growth-system dashboard shows its ROI |

## Honest status, 30 October

Designed, mostly not built. The Week 3 slice runs (one table, five routes), and
two pure-Python modules exist — `lifecycle.py` (who may move an action where)
and `roi.py` (the return calculation). On 30 October the product moved to v2
([`../product-definition-v2.md`](../product-definition-v2.md)); this page and
the portfolio plan reflect v2, while the ERD, roles, DFD, STRIDE and GDPR pages
still describe v1 and are revised in the weeks shown above.
