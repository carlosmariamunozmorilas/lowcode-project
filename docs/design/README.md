# Design pack — MarketingOps against the project brief

The *Low-Code/No-Code Project Brief* (Dr Matt Lemon, 24 October 2026) sets six
minimum requirements for every project. This folder holds the evidence for each
one, in the form the brief asks for. The technical detail behind every page is
in [`../specification.md`](../specification.md).

## The project, in the brief's own format

| Project | Users | Core app | Scheduled automation | Triggered automation | Approval step |
|---|---|---|---|---|---|
| **MarketingOps** — ROI for marketing work | An ecommerce marketing team: people who ask for work, specialists who do it, a lead who signs it off, an ops admin ❓ | Marketing actions that state their expected return and cost, are approved before the work and closed with what they achieved; realised ROI on gross profit, people's time counted as a cost; a record that cannot be rewritten | Monday intake of last week's spend and revenue figures | A new measurement that is off target opens an action for someone to take on | A named reviewer approves each action before the work starts, and separately certifies its result |

❓ **The user group has to be a real one.** The brief asks for "a real problem for
a named group of users", and the Week 4 sheet warns that contrived scenarios
mark badly. Which team, how many people, and what they do today by hand is
Carlos's to name — it is not something the design can supply.

The application is generated with an AI assistant from a written specification
(the Session 3 method) and the automations are built in **Make**, the course's
low-code platform. It is an own idea rather than one of the twenty listed, so
the brief requires it to be **agreed with the lecturer before building starts**.
The closest listed idea is project 2, IT helpdesk ticketing — the brief's own
worked example — which shares its shape: requests, an owner, a manager's
approval and an audit trail.

## The six minimum requirements

| # | Requirement | Minimum | Evidence | Page |
|---|---|---|---|---|
| 1 | Data model | ≥ 3 related tables, PKs and FKs | 12 tables; the action table links to users three times — requester, owner, named reviewer | [`erd.md`](erd.md) |
| 2 | Automations | ≥ 3: one scheduled, one event-triggered, one with a human approval step | 4: intake (scheduled) · drift alert (event) · approval routing (approval) · weekly ROI narrative (scheduled, AI) | [`../portfolio/portfolio-plan.md`](../portfolio/portfolio-plan.md) |
| 3 | Role-based access | ≥ 2 roles, enforced on the data | 5 roles; every write passes a server-side check, and the record tables are protected by database triggers | [`roles.md`](roles.md) |
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
| Short demo video of the main user journey | Week 12: an action raised, approved by its named reviewer, closed with its result, and its ROI on the project page |

## Honest status, 27 October

Designed, not built. Two pure-Python modules exist and run — `lifecycle.py`
(who may move an action where) and `roi.py` (the return calculation) — and the
schema loads. Everything else on these pages is the plan the weekly labs build
towards, and each page says which week delivers which part.
