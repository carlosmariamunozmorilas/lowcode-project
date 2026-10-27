# Week 3 slice — what the 28 October lab generates

The Session 3 brief asks for a multi-file Flask application generated from a
written specification, and says to keep **"the same shape and complexity"** as
its one-table task tracker. The full [`specification.md`](specification.md) —
twelve tables, logins, an API — is the target for the term, not for one
evening. Asking an assistant to generate all of it at once is the most likely
way to spend the lab debugging things nobody needed yet.

So tonight generates a **slice**: one table, five routes, no login — the
application's core object with its real lifecycle and its real ROI maths.
Every later week adds to this slice instead of replacing it.

## What the slice reuses

Two modules are already in the repository, tested by hand, and imported as
they are — the assistant is told **not** to rewrite them:

- [`lifecycle.py`](../lifecycle.py) — `ALLOWED`, the map of which stage may
  follow which
- [`roi.py`](../roi.py) — `investment()`, cash plus people time

Login, roles and the named-reviewer rule arrive with authentication; until
then the slice enforces the stage graph only, which is all `ALLOWED` needs.

## The specification to paste

```markdown
# MarketingOps — Week 3 slice

## Purpose
A marketing team logs every action it takes — what it is, which lever it pulls,
what it costs in cash and hours — and moves it through review to a result.
This slice replaces the spreadsheet where actions are listed today.

## Entities

### Action (table `actions`)
- id (integer, primary key)
- title (text, required, max 200)
- description (text, optional, max 2000)
- lever (text, required, one of: paid_prospecting, seo_content, email_traffic,
  checkout_friction, product_page, trust_signals, bundles, cross_sell,
  free_shipping)
- cost_eur (real, required, >= 0, default 0)
- cost_hours (real, required, >= 0, default 0)
- status (text, one of: submitted, assigned, in_review, approved, closed,
  rejected, cancelled — default submitted)
- created_at (timestamp, default now)

## Routes
| Method | Path | Does |
|---|---|---|
| GET | / | List all actions, newest first, with status and investment |
| GET | /action/new | Form to create an action |
| POST | /action | Create an action, redirect to / |
| GET | /action/<id> | Show one action, its investment, and buttons for the next legal stages |
| POST | /action/<id>/status | Change status if the move is legal, redirect back |

## Rules
- The next legal stages come from `ALLOWED` in the existing `lifecycle.py`.
  An illegal move is refused with a message; nothing is written.
- Investment = `investment(cost_eur, cost_hours, 35.0)` from the existing
  `roi.py` (35 euros per hour). Do not reimplement it.
- Do not modify `lifecycle.py` or `roi.py`.

## Technical constraints
- Python 3.11+, Flask 3.x
- SQLite via the standard library sqlite3, parameterised queries only
  (no ORM this week)
- schema.sql creates the table; app.py does not create tables at import
- Jinja2 templates in templates/, one base template
- Configuration and the secret key read from environment variables
- No authentication this week; no JavaScript framework

## Out of scope
User accounts and roles · approvals by a named reviewer · KPI targets and
measurements · ROI on gross profit · tasks and review checks · automations and
the API · charts · file attachments · search
```

## The prompt

With the specification above pasted first, in **Claude** — the tool chosen in
Week 2:

```text
Build this application. lifecycle.py and roi.py already exist in the
repository; import them, do not rewrite them. Give me every file separately,
with its full path. Do not explain the code.
```

## The order, from the Student Brief

1. `git checkout -b feature/week03-slice` — **before** generating
2. Generate; create the files; `sqlite3 marketingops.db < schema.sql`;
   `python3 app.py`; fix only what stops it starting
3. **Commit the raw generated version before improving anything** — the honest
   record of what the AI produced unaided
4. Ask a **different** assistant — Gemini or ChatGPT — to review it:
   *"Review this Flask application for correctness, structure and security.
   List concrete problems with file and line. Do not rewrite it."*
5. Record the findings in `docs/week03-review.md` in the brief's four parts:
   findings · what I fixed and why · what I am knowingly leaving and why ·
   what the reviewer got wrong
6. Fix at least two findings, **one commit each**
7. Push, open a pull request with a description in your own words, merge
8. Clean-clone test: clone → `python3 -m venv .venv` →
   `source .venv/Scripts/activate` (Git Bash on Windows) →
   `pip install -r requirements.txt` → run

## What to look for in the review

The brief's list — string-built SQL, a hardcoded or missing secret key, no
input length checks, `debug=True` — plus two that belong to this project:

- **Does the status route call `ALLOWED`**, or did the assistant copy the
  transitions into the route, where they can drift from `lifecycle.py`?
- **Does the investment come from `roi.investment()`**, or was the formula
  rewritten inline?

Either one is a finding worth writing up: an AI that duplicates a rule it was
told to import is the Week 7 bug in miniature.

## Acceptance — the Student Brief's checklist

- [ ] `docs/specification.md` written before generation — it is, and this slice
      is part of it
- [ ] Runs from a clean clone
- [ ] Multi-file: `app.py`, `templates/`, `schema.sql`, not one 200-line file
- [ ] A commit containing the unmodified generated scaffold
- [ ] `docs/week03-review.md` lists findings
- [ ] At least two fixes, each its own commit
- [ ] A merged pull request with a description in your own words
- [ ] `*.db` and `.venv/` gitignored — already true

**Before any of this:** the brief says an own idea must be agreed with the
lecturer before building starts. Tonight is when building starts.
