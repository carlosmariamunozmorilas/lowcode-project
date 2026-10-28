# Week 3 — review of the generated slice

The Session 3 brief asks for four things: the findings, what I fixed and why,
what I am knowingly leaving and why, and what the reviewer got wrong. This page
covers the [Week 3 slice](week03-slice.md): one table, five routes, no login.

## How it was made

| Step | What happened | Where |
|---|---|---|
| Branch | `feature/week03-slice`, cut from `main` before any code was generated | — |
| Generate | **Claude**, from the slice specification and its prompt, in one pass | commit `74369c5` |
| Run | `sqlite3 marketingops.db < schema.sql`, then every route through Flask's test client. It worked first time, so nothing was changed before committing | — |
| Review | **Gemini 3.5 Flash-Lite**, signed out. The other models need an account | [raw output](../experiments/week03/gemini-review.md) |
| Verify | Every claim the reviewer made, and my own checks, run against the code, not just read | below |
| Fix | Six fixes, one commit each | `d6752f2` … `6250de1` |

Two things limit how far this comparison goes, and they should be said
before the results.

- **The generator was not blind.** Claude produced the scaffold inside the
  repository session (Claude Code), where it could read `lifecycle.py` and
  `roi.py`, rather than in a fresh chat with only the pasted specification. The
  same model then helped verify and fix it. The raw commit is a genuine single
  pass, but it is not the output of a tool that knew nothing about the project.
- **The reviewer was the smallest Gemini model.** Without an account, Gemini
  offers only Flash-Lite. A stronger model might have found more, so this
  review measures Flash-Lite, not Gemini as a whole.

## The two checks this project cares about

[`week03-slice.md`](week03-slice.md) named two failures to look for before
the generic ones. **Neither happened.**

- The status route asks `ALLOWED` from `lifecycle.py` which moves are legal.
  The transitions were not copied into the route (raw `app.py` lines 135 and
  150).
- The investment comes from `roi.investment()`. The formula was not rewritten
  inline (lines 82 and 139).

So the assistant imported the rules it was told to import. The bugs it did
write are in the code around those rules, not in the rules.

## 1. Findings

Line numbers refer to the raw scaffold, commit `74369c5`. **Source** says who
raised the finding; **Verified** says what running it showed.

| # | Finding | File : line | Source | Verified |
|---|---|---|---|---|
| F1 | A hardcoded fallback secret key, `"dev"` | `app.py:34` | Gemini | True. The key is readable in the repository, so anyone could forge the session cookie |
| F2 | No way to set up the database; a missing file becomes an empty one | `app.py:41-45` | Gemini (in part) | True, and worse than reported: `sqlite3.connect` silently creates an empty file, then every page returns 500 with *no such table: actions*. The lab's setup step needs the `sqlite3` command-line tool, which Git Bash does not ship |
| F3 | `"inf"` and `"nan"` accepted as costs | `app.py:64-71` | mine | True. `inf` was stored and shown as **€inf**. `nan` passed the `< 0` check, reached SQLite as NULL and crashed with a 500 |
| F4 | The status check and the status write are separate steps | `app.py:147-158` | mine | True. When an action was cancelled between the read and the write, the stale request moved it back to `assigned`: a cancelled action brought back to life |
| F5 | "Newest first" is wrong within the same second | `app.py:77` | mine | True. Three actions created in a row listed as 3, 1, 2 |
| F6 | `requirements.txt` replaced with one loose line | `requirements.txt:1` | mine | True. `Flask>=3.0,<4.0` drops every pin, including the transitive ones. The old pins carried six `pip-audit` advisories |
| F7 | No CSRF protection on any form | `templates/detail.html:28`, `templates/new.html:5` | mine | True. A POST from another origin is accepted |
| F8 | Anyone can approve and close any action | `app.py:150` | Gemini (as F9's consequence) | True: an action walked from `submitted` to `closed` with no checks. Known and in scope, see §3 |
| F9 | The route uses `ALLOWED`, not `check_transition()` | `app.py:135, 150` | Gemini | Misread, see §4 |
| F10 | An empty cost is stored as `None` and crashes on NOT NULL | `app.py:64-71, 125` | Gemini | **False**, see §4 |
| F11 | Title and description need server-side sanitisation against XSS | `templates/detail.html:8` | Gemini | **False**, see §4 |
| F12 | After a failed submit, empty cost fields come back empty, not `0` | `templates/new.html:23, 27` | Gemini | True, and cosmetic: an empty cost is read as 0 anyway |

The scaffold got the brief's own checklist right. Every query is
parameterised, `debug` is off unless `FLASK_DEBUG=1`, the server binds to
`127.0.0.1`, both text fields are length-checked on the server and in the
schema, and Jinja2 autoescaping is on.

## 2. What I fixed, and why

One commit per fix, in this order.

1. **F3 — reject infinite and NaN costs** (`d6752f2`). A cost is a finite
   number of zero or more, and `math.isfinite` says so in one line. I fixed
   this first because it was a reachable crash *and* a nonsense number on the
   screen, which matters in an app whose purpose is to make its numbers
   trustworthy.
2. **F4 — make the status change a single check-and-write** (`ed1086e`). The
   UPDATE now also matches the status that was checked; if nothing matches,
   the user is told and nothing is written. This is the rule the full
   specification already sets for Week 7 (a status change and its history row
   in one transaction), so it is cheaper to have it right in the slice than to
   unlearn it later. A cancelled action coming back is exactly the kind of
   record an audit trail exists to prevent.
3. **F1 — no known secret key** (`9eeb1b3`). Without `SECRET_KEY`, the app now
   generates a random key for the life of the process and logs a warning. I
   chose this over refusing to start: this week the session holds only flash
   messages, the clean-clone test should work with no setup, and a deploy that
   forgets the variable now fails safe instead of running on a published key.
   Week 10 must set it for real.
4. **F5 — newest first, ties broken by id** (`55fdc08`). One clause,
   `id DESC`. The specification says newest first, and ids only grow.
5. **F2 — `flask --app app init-db`, and no silently created databases**
   (`ac037cf`). The command runs `schema.sql`, so the clean clone needs nothing
   beyond Python. The app now opens the file read-write without creating it,
   and a missing database is an error that names the command to run. Tables are
   still not created at import, as the specification requires. The README gains
   the run steps.
6. **F6 — every dependency pinned again** (`6250de1`). Flask 3.1.0 → 3.1.3 and
   Werkzeug 3.1.3 → 3.1.9. `pip-audit` reported six advisories on the old pins
   and none on the new ones. This was the upgrade recorded in Week 2 as due when
   this lab regenerated the dependencies. `click` 8.5 no longer pulls in
   `colorama` on Windows, so the Week 2 `colorama` gap is gone, not merely
   pinned.

## 3. What I am knowingly leaving, and why

- **F8, anyone can approve or close (no login, no roles).** The slice is
  specified without authentication, and `check_transition()` needs a requester,
  owner, reviewer and acting user that this one-table slice does not have. When
  login arrives, the status route must call `check_transition()`, not `ALLOWED`
  alone. Until then, nobody should put real work into this app.
- **F7, no CSRF tokens.** With no login, a forged request can do nothing that
  a visitor could not do directly, so a token would protect nothing yet. It
  arrives with login, in the same change as F8.
- **F12, empty fields re-render empty.** Cosmetic, and an empty cost already
  means 0.
- **Two schemas.** `schema.sql` (this slice) and `schema/001_initial.sql` (the
  target design, with `requests`, the history table and the append-only audit
  log) describe the same object differently. They are merged in Week 5, when
  persistence becomes that week's subject.
- **`created_at` is UTC and is shown without saying so.** It is acceptable for
  one team in Dublin for now. Times should be labelled when the weekly reports
  start reading them.
- **No test files yet.** Every claim on this page was checked by a throwaway
  script, not by a committed test. The test suite is Week 7. F3, F4 and F5 are
  its first three cases, because each was a real bug.
- **Flask's development server.** It is fine on `127.0.0.1`. Running the app
  in production is the subject of Weeks 9 and 10.

## 4. What the reviewer got wrong

Flash-Lite produced seven findings. Two were right (F1 and F2), one was right
but cosmetic (F12), and four were wrong or misread the scope.

- **F10, the empty-cost crash, does not exist.** `parse_cost` reads an empty
  field as `float("" or 0)`, which is `0.0`. And `None` can never reach the
  INSERT, because any invalid cost stops the request before it does. Tested: an
  action submitted with both costs empty is stored as `(0.0, 0.0)`. The real
  crash on that line was `"nan"` (F3), which it did not find.
- **F9, "call `check_transition()`", misreads the specification.** The slice
  says the next stages come from `ALLOWED`, and lists roles and named
  reviewers as out of scope. `check_transition()` cannot be called without an
  owner, a reviewer and an acting user, and the slice has none of them. Its
  supporting claim, that illegal moves "fail silently or cause unhandled
  exceptions", is also false: tested, an illegal move is refused with a message
  and nothing is written. Gemini counted this finding twice, once under
  correctness and once under structure.
- **F11, input sanitisation for XSS, recommends the wrong control.** The
  defence against stored XSS is escaping on output, which Jinja2 does.
  "Sanitising" input would corrupt what people typed. Its claim that
  descriptions are "rendered raw" is false: tested, a `<script>` title and an
  `<img onerror>` description both come out escaped.
- **F2 was half right.** No technical constraint was violated: the
  specification says `schema.sql` creates the table, and the slice document
  says how to run it. The real problem, an empty database created behind the
  user's back, it did not see.

What it missed matters more than what it got wrong. It found none of the
three bugs that change data (F3, F4, F5) and none of the dependency problem
(F6). And it named "CSRF protection" as something the secret key protects, in
an app that has no CSRF protection at all (F7). **Fixes 1, 2, 4 and 6 come
from my own checks, not from the review.** The lesson for Week 7 is the same
one Week 2 taught: a review is a list of claims to test, not a list of facts.
