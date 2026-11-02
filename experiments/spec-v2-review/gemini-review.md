# Gemini's review of specification v2 — raw output

**Provenance.** gemini.google.com in the Claude desktop app's built-in browser,
signed in with my Google account, model **3.1 Pro**, thinking level **High**.
2 November 2026, conversation `167db1afb8eae912`. The project's chosen reviewer
is 4 Argon on High, but my account shows it locked behind an upgrade, so 3.1
Pro High (the strongest model the account offers) was used instead, by my
decision.

**Prompt.** The text below, followed by the whole of
[`docs/specification-v2.md`](../../docs/specification-v2.md) as merged at
commit `43d378f` (46,208 characters). Claude prepared the text; I pasted it
into Gemini and sent it, because the page refused a paste triggered by Claude.
Gemini received it whole: the sent message ends with the spec's last line.

```text
Review the specification below. It is for a course MVP: a solo student, 11
weeks, Flask and SQLite, built with AI assistants. Nothing is built yet.

List concrete problems, each with its section number:
1. internal contradictions between sections;
2. rules or formulas the schema cannot support;
3. rules that cannot be tested as written;
4. security or privacy gaps;
5. what is over-built for an MVP of this size.

Do not rewrite the specification. Say when you are unsure.

--- SPECIFICATION ---
```

**Capture.** Read from the rendered page, with headings, bold and code spans
restored as Markdown. The wording is unchanged.

The triage — which findings are right, which are wrong, and what to do — is in
[`docs/spec-v2-review.md`](../../docs/spec-v2-review.md).

---

Here are the concrete problems in the specification, categorized as requested.

### 1. Internal contradictions between sections

- **API Authentication vs. Database Users (Sections 1, 3, 5, 8):** Section 3 defines an `is_service` flag in the `users` table and a `service` role in `user_roles`. Section 5 states the `service` role writes through the signed API. However, Sections 1 and 8 state that automations authenticate via HMAC using "one API secret per automation" stored in `config.py`. It is contradictory/unclear how an HMAC-authenticated incoming request maps to a specific `user_id` in the database to fulfill database constraints (like `actor_id` or `recorded_by`) if the secrets live in the environment rather than being tied to the `users` table.
- **Cost handling (Sections 3 vs. 4):** Section 4 states that for the Growth P&L, "Discounts... [are] already inside net revenue". However, Section 3 defines the `orders` table as having `net_revenue_eur (after discounts)` *and* `discount_eur`. If the goal is not to subtract them twice, storing `discount_eur` on the order alongside a pre-subtracted `net_revenue_eur` risks double-counting if future queries aren't perfectly written. Furthermore, Section 4 states contribution subtracts refunds, but refunds live in a separate table (Section 3), meaning they cannot be simply subtracted at the individual *order* row level without a `JOIN` and handling date discrepancies.

### 2. Rules or formulas the schema cannot support

- **Cross-table `CHECK` constraints (Sections 3 & 5):** SQLite does not support subqueries in `CHECK` constraints. Therefore, the schema *cannot* enforce the following rules at the database level:
  - `client_reports`: "reviewed_by FK → users (a person, never a service account)" (requires checking `is_service` in the `users` table).
  - `actions` / `assignments`: Ensuring the `reviewer_id` actually holds the `lead` role (requires checking `user_roles`).
  - `actions`: Ensuring the reviewer is actually assigned to the client (requires checking `client_assignments`).

  These will have to be enforced strictly in application logic (`lifecycle.py`), not the schema.
- **Enforcing the "Measurement Period" for Early Stops (Sections 3 & 5):** The rule that an action cannot close early without an `early_stop_reason` requires comparing the current date to `window_end` + `post_period_days`. A SQLite `CHECK` constraint cannot reliably validate dynamic temporal rules involving `CURRENT_TIMESTAMP`.

### 3. Rules that cannot be tested as written

- **Test 18: API HMAC Validation (Sections 6, 8, 11):** The test says "POST /api/events refuses a bad signature." Because there is "one API secret per automation" (Section 8), the server must know *which* secret to use to validate the HMAC. An HMAC signs the payload, but the payload or header must first transmit a plaintext identifier (e.g., the automation name or `source`) so the server knows which secret to hash against. The spec does not define how this lookup occurs, making the exact security handshake untestable as written.
- **Test 29: Incomplete P&L lines (Sections 3, 4, 11):** The test dictates that missing product costs make dependent Growth P&L lines "incomplete" rather than zero. In SQL, aggregation functions like `SUM(product_cost_eur)` automatically ignore `NULL` values and return the sum of the remaining rows. To pass this test, the raw SQL queries cannot just use `SUM()`; they will require complex conditional logic (e.g., `CASE WHEN COUNT(product_cost_eur) < COUNT(*) THEN NULL ELSE SUM(product_cost_eur) END`) to actively detect and propagate the "incomplete" state.

### 4. Security or privacy gaps

- **GDPR / Privacy Misinterpretation (Sections 3 & 8):** Section 3 states "the only personal data is the team's own user records" because `customer_ref` is a "pseudonymous code". This is legally incorrect. Under the GDPR (Article 4(5)), pseudonymized data that can be used to single out an individual or track their behavior over time (which the `assignments` and `orders` tables explicitly do) remains classified as Personal Data. The system must treat shop data as PII.
- **Replay Attacks on the API (Sections 3, 6, 8):** While the HMAC signature verifies payload integrity, a basic HMAC without a timestamp or nonce is vulnerable to replay attacks. Section 3 includes `UNIQUE (source, external_id)` which provides idempotency and mitigates *some* replays, but if a record is somehow altered, an attacker intercepting the payload could resend a valid signed payload to force the system into a previous state.

### 5. What is over-built for an MVP of this size

- **Idempotent, Webhook-based Data Intake (Sections 3, 8):** Building a Make.com automation that batches shop data, calculates control totals (`expected_rows`, `expected_revenue_eur`), and sends HMAC-signed payloads to an idempotent Flask endpoint is massive scope creep. For an 11-week solo MVP, a simple manual CSV file upload route in Flask would save weeks of engineering.
- **Database Triggers for Append-Only Ledger (Section 3):** Implementing SQLite triggers to actively abort `UPDATE` and `DELETE` on `action_history` and `component_months`, combined with a self-referencing `supersedes_id` to handle corrections, is extreme for an MVP. A standard update model with a basic application-level audit log is much more realistic for 11 weeks.
- **Fictional Data Generator (Section 9):** Writing a Python script to generate 6 months of coherent, daily e-commerce data featuring seasonal variance, refunds, matching ad-spend, and perfectly mapped statistical holdout test results across three different fictional stores is a complex data-science project of its own, threatening the time needed to build the actual Flask application.
- **Dynamic Per-Customer Holdout Calculation (Section 4):** Calculating the exact contribution difference dynamically from raw `orders` joined to `assignments` (including customers who bought nothing) using raw SQLite queries on the fly is highly complex and likely to cause significant performance or SQL-authoring bottlenecks for a solo student.
