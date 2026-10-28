# Week 3 — review of the first working version

This review covers the [Week 3 slice](week03-slice.md) of MarketingOps: one table, five routes and no login. It records the findings, the fixes, the limitations left for later and the mistakes in the AI review.

MarketingOps is intended to help an ecommerce marketing team assess the return from its work. This first version only records actions, costs, investment and status changes. It does not yet implement the complete ROI and approval workflow.

## How the code was generated and checked

The branch `feature/week03-slice` was created before generating the code. Claude Code generated the scaffold from the slice specification in one pass. The database was initialised with `sqlite3 marketingops.db < schema.sql`, and the routes were exercised through Flask's test client. The scaffold ran successfully and was committed unchanged as `74369c5`.

Gemini 3.5 Flash-Lite then reviewed it in a signed-out session. The [original response](../experiments/week03/gemini-review.md) is preserved. Its claims were checked against the code, and additional checks were carried out with Claude's assistance. Six fixes followed, each in its own commit.

There are two important limits to this exercise:

- **The generator was not blind.** Claude worked inside the existing repository, where it could read `lifecycle.py` and `roi.py`. It also helped verify and fix the generated code.
- **The reviewer was Flash-Lite.** This was the model available in the signed-out session. These results should not be treated as a judgement of every Gemini model.

The findings labelled “additional checks” below correspond to the original review's “mine” category. They were separate from Gemini's review, but were checked with Claude's assistance; they should not be read as unaided discoveries.

## Reusing the existing project rules

Two project-specific checks passed:

- The status route uses `ALLOWED` from `lifecycle.py`, rather than copying the transition rules into the route: raw `app.py` lines 135 and 150.
- Investment uses `roi.investment()`, rather than repeating the formula: raw `app.py` lines 82 and 139.

The scaffold therefore reused the existing rules as requested. The problems below were in the surrounding implementation.

## 1. Findings

All line references refer to the original scaffold, commit `74369c5`.

| ID | Finding | Reference | Source | Recorded verification |
|---|---|---|---|---|
| F1 | Predictable fallback secret key, `"dev"` | `app.py:34` | Gemini | Confirmed. A known key allows session cookies to be forged. |
| F2 | Database setup is inconvenient, and a missing database becomes an empty file | `app.py:41-45` | Gemini, partly; additional checks | Confirmed. The empty file causes a 500 error with `no such table: actions`. The original setup also requires the SQLite command-line tool, which Git Bash does not include. |
| F3 | Infinite and NaN costs are accepted | `app.py:64-71` | Additional checks | Confirmed. `inf` displays as €inf; `nan` reaches SQLite as NULL and causes a 500 error. |
| F4 | Checking and updating status are separate operations | `app.py:147-158` | Additional checks | Confirmed. A concurrent cancellation can be overwritten, moving the action back to `assigned`. |
| F5 | Newest-first ordering is unreliable within the same second | `app.py:77` | Additional checks | Confirmed. Three actions appeared in the order 3, 1, 2. |
| F6 | Exact dependency versions were replaced with a broad version range | `requirements.txt:1` | Additional checks | Confirmed. `Flask>=3.0,<4.0` removed the pins. The previous pinned versions also had six reported security advisories. |
| F7 | Forms have no CSRF tokens | `templates/detail.html:28`, `templates/new.html:5` | Additional checks | Confirmed. A POST from another origin is accepted. |
| F8 | Anyone can approve or close actions | `app.py:150` | Gemini, through F9; additional verification | Confirmed. There is no authentication or role enforcement in this slice. |
| F9 | Using `ALLOWED` instead of `check_transition()` violates the requirements | `app.py:135, 150` | Gemini | Misreads the scope. See section 4. |
| F10 | Empty costs are inserted as `None` and crash the database | `app.py:64-71, 125` | Gemini | Incorrect. Empty costs become zero. |
| F11 | Title and description are displayed without protection against XSS | `templates/detail.html:8` | Gemini | Incorrect for the tested templates. Jinja2 escapes the output. |
| F12 | Empty cost fields remain empty after a validation error | `templates/new.html:23, 27` | Gemini | Confirmed, but cosmetic. Empty costs are interpreted as zero. |

The original scaffold also passed several basic checks: parameterised queries, debugging off unless `FLASK_DEBUG=1`, binding to `127.0.0.1`, text-length checks in the application and schema, and Jinja2 autoescaping.

## 2. What was fixed, and why

Claude assisted with all six fixes.

- **Reject invalid costs — F3, `d6752f2`.** Costs must be finite numbers of zero or more. `math.isfinite()` rejects infinity and NaN. This removes a crash and prevents meaningless investment figures.
- **Protect concurrent status changes — F4, `ed1086e`.** The update now checks that the action still has the status previously read. If another request changed it, nothing is overwritten and the user is asked to try again. This protects the status update; the complete transactional history remains part of the wider design.
- **Remove the predictable secret key — F1, `9eeb1b3`.** If `SECRET_KEY` is missing, the app generates a random key for that process and logs a warning. This keeps local setup straightforward while removing the published fallback key. A stable, securely configured key is still required for deployment in Week 10.
- **Resolve ordering ties — F5, `55fdc08`.** Adding `id DESC` puts newer actions first when their creation timestamps match.
- **Add database initialisation — F2, `ac037cf`.** `flask --app app init-db` creates the tables from `schema.sql` without requiring a separate SQLite command-line installation. Normal database access no longer silently creates a missing file. The README explains the setup, and tables are not created when the module is imported.
- **Restore and update dependency pins — F6, `6250de1`.** Flask moved from 3.1.0 to 3.1.3 and Werkzeug from 3.1.3 to 3.1.9, with exact versions recorded for all dependencies. The recorded `pip-audit` check on 28 October reported no advisories, compared with six on the previous pins. With click 8.5, `colorama` was no longer pulled in on Windows.

## 3. What remains, and why

- **No login or permissions — F8.** This slice deliberately excludes users and roles. The full `check_transition()` function requires information that the one-table version does not have. Authentication and server-side permission checks must be added before using it for real work.
- **No CSRF tokens — F7.** These are deferred to the authentication work. Because all visitors can already change actions, the slice has a broader access-control limitation. The absence of login does not make CSRF protection unnecessary for the finished application.
- **Empty fields stay empty — F12.** This is a display issue; empty costs are still processed as zero.
- **Two schemas.** `schema.sql` runs this slice. `schema/001_initial.sql` describes the fuller design, including history and audit records. They are scheduled to be reconciled in Week 5.
- **Unlabelled UTC timestamps.** `created_at` is UTC, but the interface does not say so. The display should identify the timezone.
- **No committed test suite.** Verification used temporary scripts. The suite is planned for Week 7, with F3, F4 and F5 providing concrete regression cases.
- **Development server only.** This version runs locally on `127.0.0.1`. Production packaging and deployment belong to Weeks 9 and 10.

## 4. What the reviewer got wrong

Gemini produced seven findings: two held, one was cosmetic, and four were incorrect or misread the scope. F9 appeared twice, under correctness and structure.

- **Empty costs did not cause the claimed crash — F10.** The expression `float("" or 0)` produces `0.0`. Submitting both costs empty stored `(0.0, 0.0)`. Invalid parsed costs were stopped before insertion. The actual crash involved `"nan"`, which Gemini missed.
- **`ALLOWED` matched the slice specification — F9.** This version was explicitly required to use the transition graph without implementing roles or named reviewers. The fuller permission function needs those details. Illegal transitions were also refused with a message and no database change, rather than failing silently as the review suggested.
- **The tested output was escaped — F11.** A `<script>` title and an `<img onerror>` description were rendered as escaped text. The claim that descriptions were displayed raw was incorrect. Escaping output in these templates was the relevant protection.
- **The database finding was only partly explained — F2.** Setup instructions already existed, so the absence of automatic table creation was not itself a specification violation. The additional checks exposed the more useful problem: a missing database was silently created empty.

Gemini missed F3, F4, F5 and F6, which led to four of the six fixes. It also referred to CSRF protection when discussing the secret key, although the application had no CSRF tokens.

The practical lesson is to check an AI review against the specification and reproduce its claims. A convincing explanation can still describe a bug that does not exist, while missing one that does.
