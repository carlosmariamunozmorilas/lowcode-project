# AI-usage log: MarketingOps v2 (Scaling)

This log is a graded part of CA2 and feeds the AI Fluency declaration
(Delegation, Description, Discernment, Diligence). Prompts are pasted exactly
as typed. **The log starts on 14 November 2026.** Earlier AI work is recorded
elsewhere in the repository: the tool comparison in `experiments/week02/`, the
Week 3 review in `docs/week03-review.md`, and Gemini's reviews of the
specification and the code in `experiments/spec-v2-review/` and
`experiments/v2-code-review/`.

The fields marked ✍️ (the decision and why) are Carlos's to write.

## Tools I used

| Tool | Version or plan | What I used it for |
|---|---|---|
| Claude Code | desktop app, Claude Opus 5.5 | building and testing the app, the Make automations through Make's API, documents |
| Gemini | 3.1 Pro (High), signed in | independent reviews of the specification (2 Nov) and the code (2 Nov) |
| ChatGPT | free | third tool in the Week 2 comparison |

## Log entries

---

### Entry 1: Test the webhook with bad input (Session 4, Block 2)

- **Date:** 2026-11-14
- **Tool:** Claude Code (Claude Opus 5.5)
- **Task (why I used AI here):** ✍️
- **Prompt (verbatim):** answering Claude Code's offer to *"send the app's
  signed `POST /api/events` the bad inputs the brief lists … show that each one
  gets a 400 error, not a crash"*:

  ```text
  Yes, webhook tests
  ```

  and, after it reported that 100,000-character values were accepted:

  ```text
  Cap long values first
  ```

- **What it produced:** `tests/test_api_bad_input.py` (30 bad-input cases) and
  fixes in `routes/api.py`: 11 inputs that crashed with a 500 now get a 4xx;
  length limits on ids and text. Pull request #34.
- **Decision:** ✍️ Accepted / Modified / Rejected
- **Why:** ✍️
- **What I checked:** ✍️ *(the tests were run: full suite 129 passed, ruff clean)*
- **Decisions the AI made that I did not specify:** the limits (100 characters
  for ids, 200 for other short text, 20,000 for a report draft); which status
  codes to use (400 for a malformed body, 422 for bad rows); checking all four
  row lists before writing anything; the 30 test cases themselves.
- **Commit:** `d2957d3 Refuse bad webhook input with a 4xx instead of crashing`

---

### Entry 2: Answer 21 open decisions in one message

- **Date:** 2026-11-14
- **Tool:** Claude Code (Claude Opus 5.5)
- **Task (why I used AI here):** ✍️
- **Prompts (verbatim):**

  ```text
  give me the complete to do list, put separately all the items that implies making decision i could answer all at the same time with one prompt
  ```

  ```text
  give me all the recommendations you can and above the options point the one you would recommend me
  ```

  The answer was written in Spanish; English translation (the original is in
  the session transcript): *"OK, I'm going to choose the options from the
  recommendation list I asked you for a moment ago, so I'll tell you them one by
  one. 1A, 2A, 3B, 4A, 5A, 6B, 7A, 8A, 9A, 10A, 11A, 12A, 13A, 14A, 15A, 16A,
  17A, 18A, 19A, 20A, 21A."*
- **What it produced:** a decision list with a recommendation and a reason for
  each; the choices recorded in the to-do list and acted on (PRs #31, #34, #35;
  automation 1's signer and fallback warning in Make).
- **Decision:** ✍️
- **Why:** ✍️ *(every recommendation was taken: worth a sentence on whether
  that was judgement or delegation)*
- **What I checked:** ✍️
- **Decisions the AI made that I did not specify:** the wording of each option
  and which one to recommend; the fallback warning's text in Make.
- **Commit:** `5d0c87c` (PR #31), `d2957d3` (PR #34), PR #35

---

### Entry 3: The Session 5 lab on an app whose schema already existed

- **Date:** 2026-11-14
- **Tool:** Claude Code (Claude Opus 5.5)
- **Task (why I used AI here):** ✍️
- **Prompt (verbatim):**

  ```text
  Session 5 lab first
  ```

  (choosing between the Session 5 lab and the automation 1 AI step, which
  Claude Code had offered as the next two items)
- **What it produced:** the kit added with three rules adapted (`AGENTS.md`);
  `docs/data-model.md` with the field tables generated from the schema, a
  Mermaid ERD and four things to look at; `tools/check_db.py` run and its
  output saved; the restart test done in the browser on a scratch database;
  `tests/test_constraints.py` (13 tests); the predict-then-prove sheet.
- **Decision:** ✍️
- **Why:** ✍️
- **What I checked:** ✍️
- **Decisions the AI made that I did not specify:**
  - generating the field tables from the SQL instead of writing them by hand;
  - writing the data model after the schema, and saying so at the top of it;
  - adapting three kit rules in `AGENTS.md` (`flask init-db`, `connect()`,
    pytest) instead of following them as written;
  - leaving the 11 f-string lines flagged by `check_db.py` unchanged, for
    Carlos to decide;
  - which constraint tests to write, and a fixed-SQL helper in them so the new
    file adds no f-string;
  - a scratch copy of the demo database for the restart test, and a second
    launch configuration (`restart-test`, port 5001) to run it.
- **Commit:** `153c310`, `f8c0c64`, `5697082`, `582f909`
