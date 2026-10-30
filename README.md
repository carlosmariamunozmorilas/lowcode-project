# MarketingOps — ROI for marketing work

A workflow application for marketing teams in which every piece of work has to
justify itself. Each action names the KPI it is meant to move, by how much and
at what cost; it is reviewed and approved; and it is closed with what it
actually achieved. The application then computes its real return — on gross
profit, with people's time counted as a cost — and keeps a record that cannot
be quietly rewritten.

> Every piece of marketing work has to justify itself, and the record shows
> whether it did.

**Version 2 (30 October 2026):** the application is becoming a growth
consultancy tool for a marketing agency that advises several online stores and
builds growth systems for them — marketing, growth, automations and AI agents —
judged on real return. Growth is the method; ROI is the scoreboard. The client
stores and their data are fictional. See
[`docs/product-definition-v2.md`](docs/product-definition-v2.md); nothing of v2
is built yet.

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
on a ROAS report returns the most. And the application can say so before a
euro is spent: the campaign needs €13,375 of extra revenue to break even, while
its own hypothesis only claims €9,600. These figures come from
[`roi.py`](roi.py), not from a spreadsheet.

## What it never counts

- **Saved hours as money.** People's time is a cost. Hours an action "frees up"
  become a saving only when spending actually falls.
- **ROAS or platform-attributed revenue as a result.** Only the measured change
  in the store's own figures is.
- **ROI percentages added together.** A project's return is total profit change
  against total investment.
- **A result as more certain than it is.** Every realised figure says whether it
  rests on a holdout test, a before-and-after comparison or a correlation.

The rules around the return — fix the prediction before the result, close every
action with a decision, show the break-even point, never count saved hours as
money — follow my own *ROI AI Influence Model* series.

## Against the project brief

The course's project brief sets six minimum requirements. Where each one is
answered, for product v2. Pages marked *v1* are being revised for v2 in the
week shown.

| Requirement | Here |
|---|---|
| Data model, ≥ 3 related tables | 10 tables in the v2 MVP — [product definition v2](docs/product-definition-v2.md); [ERD](docs/design/erd.md) *v1, revised for Week 5* |
| Automations: scheduled, event-triggered, human approval | Daily shop-data intake · below-target alert when a client's new data lands · approval routing to a named lead, plus a monthly client report drafted by a read-only AI — [portfolio plan](docs/portfolio/portfolio-plan.md) |
| ≥ 2 roles, enforced on the data | Consultant, lead and admin; each consultant sees only their assigned clients, and nobody approves their own work — [roles](docs/design/roles.md) *v1, revised for Week 5* |
| Level-1 data flow diagram | [DFD](docs/design/dfd.md) *v1, revised for Week 8* |
| STRIDE threat analysis | [STRIDE](docs/design/stride.md) *v1, revised for Week 8 — adds one consultant reaching another's clients* |
| Data protection | Staff data only; the fictional orders hold no customer names or contact details — [GDPR](docs/design/gdpr.md) *v1, revised for Week 11* |

## Run it

In Git Bash on Windows (on macOS or Linux the activate script is
`.venv/bin/activate`):

```bash
python3 -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
flask --app app init-db
python app.py
```

Then open <http://127.0.0.1:5000>. `SECRET_KEY` and `DATABASE_PATH` are read
from the environment; without a `SECRET_KEY` the app makes a random one for
each run and says so.

## What is where

| | |
|---|---|
| [`docs/overview.md`](docs/overview.md) | the application in plain English |
| [`docs/influence-models.md`](docs/influence-models.md) | where the ideas come from: my influence models, and what the application takes from them |
| [`docs/design/`](docs/design/README.md) | the design pack against the brief: ERD, roles, DFD, STRIDE, GDPR |
| [`docs/specification.md`](docs/specification.md) | the technical design: entities, routes, tests, security |
| [`docs/week03-slice.md`](docs/week03-slice.md) | the first small slice the Week 3 lab generates |
| [`docs/product-definition-v2.md`](docs/product-definition-v2.md) | **the current direction (30 October 2026):** a growth consultancy tool for an agency serving several online stores |
| [`docs/week03-review.md`](docs/week03-review.md) | that slice reviewed by a second assistant: findings, fixes, what was left and what the reviewer got wrong |
| [`app.py`](app.py), [`templates/`](templates/), [`schema.sql`](schema.sql) | the running slice: one table, five routes |
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

Week 3, as of 28 October 2026.

- **Week 1** — repository, a minimal Flask application, and the project idea above.
- **Week 2** — Claude, Gemini and ChatGPT compared on the same prompt, with the
  raw output kept in `experiments/week02/`. Claude chosen for the main build:
  [`docs/week02-tool-comparison.md`](docs/week02-tool-comparison.md).
- **Week 3** — the specification is rewritten for the ROI layer and aligned
  with the project brief, and its core rules already run: `lifecycle.py`,
  `roi.py` and the schema. On 28 October the first slice of the application
  was generated from the specification by Claude, reviewed by Gemini, and
  fixed in six separate commits: [`docs/week03-review.md`](docs/week03-review.md).

**Dependencies.** `requirements.txt` pins every package, transitive ones
included. The Week 3 lab moved Flask 3.1.0 → 3.1.3 and Werkzeug 3.1.3 → 3.1.9,
clearing the six advisories `pip-audit` reported on 21 October; on 28 October
it reports none.
