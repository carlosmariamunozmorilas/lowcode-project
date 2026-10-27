# MarketingOps — ROI for marketing work

A workflow application for marketing teams in which every piece of work has to
justify itself. Each action names the KPI it is meant to move, by how much and
at what cost; it is reviewed and approved; and it is closed with what it
actually achieved. The application then computes its real return — on gross
profit, with people's time counted as a cost — and keeps a record that cannot
be quietly rewritten.

> Every piece of marketing work has to justify itself, and the record shows
> whether it did.

**New here?** [`docs/overview.md`](docs/overview.md) explains the whole
application in plain English, around one example.

Built for the CCT College Dublin *Certificate in Low-Code, No-Code & AI-Assisted
Application Development* (QQI Level 7, Oct 2026 – Jan 2027). All data is
invented: no real store, no real customers, no real figures.

## Why ROI, not ROAS

Most marketing dashboards report ROAS — revenue divided by ad spend. It ignores
margin and it ignores people's time. Three actions in one store, at 40% margin:

| Action | ROAS | ROI |
|---|---|---|
| Remove forced sign-up at checkout — 24 hours of work, no cash | n/a | **3.29** |
| Meta prospecting campaign — €5,000 and 10 hours | 1.92 | **−0.28** |
| Two product bundles — €800 and 8 hours | 3.75 | **0.11** |

The campaign that looks healthy on ROAS loses money. The fix that never appears
on a ROAS report returns the most. These figures come from
[`roi.py`](roi.py), not from a spreadsheet.

## Against the project brief

The course's project brief sets six minimum requirements. Where each one is
answered:

| Requirement | Here |
|---|---|
| Data model, ≥ 3 related tables | 12 tables — [ERD](docs/design/erd.md) |
| Automations: scheduled, event-triggered, human approval | Monday intake · drift alert on each new figure · approval routing to a named reviewer, plus an AI weekly report — [portfolio plan](docs/portfolio/portfolio-plan.md) |
| ≥ 2 roles, enforced on the data | 5 roles, four layers of enforcement — [roles](docs/design/roles.md) |
| Level-1 data flow diagram | [DFD](docs/design/dfd.md) |
| STRIDE threat analysis | 18 threats on 11 boundary-crossing flows — [STRIDE](docs/design/stride.md) |
| Data protection | staff data only, no customer data — [GDPR](docs/design/gdpr.md) |

## What is where

| | |
|---|---|
| [`docs/overview.md`](docs/overview.md) | the application in plain English |
| [`docs/influence-models.md`](docs/influence-models.md) | where the ideas come from: my influence models, and what the application takes from them |
| [`docs/design/`](docs/design/README.md) | the design pack against the brief: ERD, roles, DFD, STRIDE, GDPR |
| [`docs/specification.md`](docs/specification.md) | the technical design: entities, routes, tests, security |
| [`docs/week03-slice.md`](docs/week03-slice.md) | the first small slice the Week 3 lab generates |
| [`docs/project-definition.md`](docs/project-definition.md) | scope, invariants and the week-by-week plan |
| [`docs/portfolio/portfolio-plan.md`](docs/portfolio/portfolio-plan.md) | the four automations — the 40% portfolio |
| [`lifecycle.py`](lifecycle.py) | who may move an action to which stage, and what each stage requires |
| [`roi.py`](roi.py) | investment, incremental revenue and profit, ROI |
| [`schema/001_initial.sql`](schema/001_initial.sql) | the database, with its append-only record |
| [`docs/week02-tool-comparison.md`](docs/week02-tool-comparison.md) | Claude, Gemini and ChatGPT on the same prompt, measured |
| [`experiments/week02/`](experiments/week02/) | the raw output of all three tools behind that comparison |

## Project idea

Every marketing team I have worked in loses the same thing: the request. A sales
rep asks for a one-pager in Slack, someone else emails about a landing page, a
third request arrives in a meeting. Nobody can say what was asked, who owns it,
or whether it shipped. The usual fix is a Jira project nobody fills in, or a
spreadsheet that goes stale in three weeks.

If it took an evening instead of a quarter, I would build a marketing operations
workflow tool: submit a request, route it to an owner, review it against a
checklist, approve it, and log every transition so the trail is auditable.

The point is not the task list. It is the approval record — who approved what,
when, and whether they were allowed to. That is the part every team I have seen
does on trust and cannot evidence.

### How the idea evolved

*22 October 2026.* The note above, from Week 1, describes a request tracker with
an auditable approval trail. Before any of it was built, the idea grew one
layer: an approval record shows who signed the work off, but not whether the
work was worth doing. So every request became an action that states its
expected return and is closed with its real one. The tracker, the approval rule
and the append-only record all remain; the ROI layer sits on top.

## Status

Week 3, as of 27 October 2026.

- **Week 1** — repository, a minimal Flask application, and the project idea above.
- **Week 2** — Claude, Gemini and ChatGPT compared on the same prompt, with the
  raw output kept in `experiments/week02/`. Claude chosen for the main build:
  [`docs/week02-tool-comparison.md`](docs/week02-tool-comparison.md).
- **Week 3** — the specification is rewritten for the ROI layer and aligned
  with the project brief, and its core rules already run: `lifecycle.py`,
  `roi.py` and the schema. A first slice of the application is generated from
  the specification in the lab on 28 October.

**Known issue.** `requirements.txt` pins Flask 3.1.0 and Werkzeug 3.1.3, which
carry six known advisories (`pip-audit`, 21 October 2026). The upgrade is due
when the Week 3 lab regenerates the dependencies.
