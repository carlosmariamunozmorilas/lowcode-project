# Gemini's review of the v2 code — raw output

**Provenance.** gemini.google.com in the Claude desktop app's built-in browser,
signed in with my Google account, model **3.1 Pro**, thinking level **High**
(4 Argon is locked behind an upgrade on this account). 2 November 2026,
conversation `c9093311cd506640`.

**What was reviewed.** Eight core files at git tag `v2-baseline` (commit
`d7380d9`): `schema/002_v2.sql`, `lifecycle.py`, `roi.py`, `measure.py`,
`auth.py`, `routes/actions.py`, `routes/components.py`, `routes/api.py` —
2,471 lines, each prefixed with its line number. Templates, the dashboard
routes, the data generator and the tests were left out on purpose.

**Prompt.** The text below, followed by the eight files. Claude built the
bundle from the tag and put it on my clipboard; I pasted it and sent it. It
arrived whole: the sent message ends with line 284 of `routes/api.py`.

```text
Review the code below for correctness and security. Do not rewrite it, and do
not suggest new features or a different stack. Say when you are unsure.

CONTEXT
- A course project (CCT College Dublin, Low-Code / No-Code / AI-Assisted
  Application Development microcredential): one solo student, 11 weeks. The
  stack is fixed by the course: Python 3.11, Flask 3.1, SQLite with raw
  parameterised SQL and no ORM; PostgreSQL, Docker and deployment come in
  later weeks.
- The project brief's minimum requirements: at least 3 related tables; at
  least 3 automations (one scheduled, one triggered by an event, one with a
  human approval step) — they are Make scenarios that reach the app only
  through the signed API in routes/api.py; at least 2 roles enforced on the
  data, not by hiding buttons; a data-flow diagram; STRIDE on flows that cross
  a trust boundary; a GDPR write-up.
- The app is a tool for a marketing agency advising three fictional online
  stores. All shop data is fictional and generated; customers are
  pseudonymous codes.
- The code was generated with Claude Code from a written specification. This
  is that first version, git tag v2-baseline. Templates, the dashboard routes
  and the data generator are left out on purpose.

RULES THE CODE MUST ENFORCE
1. Nobody approves, rejects or closes an action they requested or own,
   whatever their roles; admin is no exception; only the named reviewer, who
   must be a lead assigned to the client.
2. Client isolation: a user who changes an id in a URL gets 404, never another
   client's data; admin may read every client but not change them.
3. action_history and component_months are append-only; every status change
   and its history row are written in one transaction.
4. Each benefit is counted once per client and month (benefit_key).
5. A missing cost is incomplete, never zero; a result built on it cannot close
   an action.
6. Saved hours are capacity, never money. ROAS is a diagnostic, never a result.
7. A shop-data batch is all or nothing against its control totals; a
   redelivered external_id changes nothing.
8. Each automation has its own secret and may use only its own event types.
9. Fields the workflow owns (status, measured result, decision) can never be
   set from a form.

WHAT TO LIST
Concrete problems, each with file and line number:
1. bugs: wrong results, crashes, edge cases;
2. security issues: access control, injection, CSRF, API authentication,
   information leaks;
3. any of the nine rules above that the code does not actually enforce;
4. money calculations that are wrong.
For each, say how sure you are.

--- CODE (each line is prefixed with its line number) ---
```

**Two failed attempts first.** Gemini's "Import code" from GitHub (with the
tag, then with `main`) delivered the repository as an archive Gemini could not
read; neither conversation reviewed anything. Importing needed my GitHub
account linked to Gemini, which I did for this.

**Capture.** Read from the rendered page, with headings, bold and code spans
restored as Markdown. The wording is unchanged.

The triage is in [`docs/v2-code-review.md`](../../docs/v2-code-review.md).

---

Here is a review of the code against your requirements, listing concrete bugs, un-enforced rules, security issues, and money calculation flaws.

### 1. Rule 4 Violation & Money Calculation Error (High Confidence)

**File:** `schema/002_v2.sql` (lines 205-207) and `measure.py` (lines 568-580)

- **The Problem:** The `UNIQUE INDEX component_months_benefit_once` aggressively enforces Rule 4 at the database level by rejecting any insert that shares a `client_id`, `month`, and `benefit_key` (if the benefit is not null). If two running components correctly target the same outcome and share a `benefit_key`, the second component's monthly record is blocked entirely. This breaks the financial accounting because the second component's **operating costs** and **hours** for that month cannot be recorded at all.
- **The Calculation Error:** `roi.py` (line 196) handles the deduplication correctly in Python by skipping the benefit but counting both costs. However, `measure.py`'s `stage_summary()` function (lines 578-579) completely ignores `benefit_key` deduplication. If the SQL index constraint were removed so both components could be recorded, `stage_summary` would blindly sum `r["measured_benefit_eur"]`, mathematically double-counting the benefit and violating Rule 4 in the UI.

### 2. Rule 7 Violation & Concurrency Crash (High Confidence)

**File:** `routes/api.py` (lines 100-108 and 122-131)

- **The Problem:** There is a Time-of-Check to Time-of-Use (TOCTOU) race condition in the API's webhook idempotency logic. If Make concurrently delivers the exact same `shop_data` batch twice, both threads will pass the `SELECT 1` uniqueness check (line 100). The first thread will write the `orders` and commit an `accepted` event. The second thread will hit an `IntegrityError` when trying to insert the identical `orders` (due to the unique `external_id`) and fall into the `except` block to execute `_reject()`.
- **The Crash:** Inside `_reject()`, the app attempts to insert a `status = 'rejected'` row into `automation_events`. Because `'rejected' <> 'duplicate'`, this trips the `automation_events_once` partial unique index (which only exempts duplicates). The second thread crashes with an unhandled 500 Server Error instead of safely treating the redelivered payload as a duplicate or 422.

### 3. Edge-Case Logic Bug: Un-Retiring Components (Moderate Confidence)

**File:** `routes/components.py` (lines 149-151)

- **The Problem:** When a lead changes a component's status to `retired`, the SQL query correctly sets `retired_on = date('now')`. However, if the lead moves the component back to `running` or `review_due`, the `ELSE retired_on` clause leaves the stale retirement date permanently attached to the component.

### 4. Edge-Case Logic Bug: Assumed Defaults in P&L (High Confidence)

**File:** `measure.py` (lines 234-236 and 258-259)

- **The Problem:** Rule 5 states "A missing cost is incomplete, never zero". When computing the overall `period_pnl`, the SQL query uses `COALESCE(SUM(product_cost_eur), 0)`. Because `SUM()` skips `NULL` values, missing costs are mathematically treated as zero when calculating `before_marketing` (line 258). While the response correctly flags the row as `any_missing = True` to warn the user, the literal numeric value calculated for the dashboard assumes the missing costs were zero.

### Security & Rule Adherence Notes

- **Rule 1 (Reviewer Roles):** Solid. `lifecycle.py` explicitly blocks the requester/owner from acting as the reviewer, and `routes/actions.py` structurally forces the reviewer to be pulled from `eligible_lead_ids()`.
- **Rule 2 (Client Isolation):** Solid. `get_client(write=True)` accurately restricts modification to assigned users. An admin cannot bypass this to write because they will not be in `assigned_client_ids()`.
- **Rule 8 (Automation Secrets):** Solid. `hmac.compare_digest` safely authenticates raw request bodies, preventing timing attacks and unauthorized event dispatching.
- **Rule 9 (Workflow Fields):** Solid. `read_form()` explicitly allows only white-listed tuples, acting as an effective barrier against Mass Assignment (IDOR) attacks on strictly controlled fields.
- **CSRF / Injection:** Solid. Global `check_csrf` protects all state-changing endpoints except the intentionally exempt API. All DB queries use parameterized inputs (`?`).
