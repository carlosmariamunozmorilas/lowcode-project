# Gemini's review of the Week 3 scaffold — raw output

**Provenance.** gemini.google.com, signed out, model **3.5 Flash-Lite** (the
only model offered without an account; 3.6 Flash, 3.1 Pro and 4 Argon were
greyed out). 28 October 2026, about 18:20 Dublin time, conversation
`e784d38ccc58baa4`. Signed-out conversations are not kept in a Gemini history,
so this file is the only copy.

**Prompt.** The review prompt from [`docs/week03-slice.md`](../../docs/week03-slice.md),
then a note that `lifecycle.py` and `roi.py` were imported rather than generated,
then the slice specification, then every file of the raw scaffold (commit
`74369c5`) with line numbers, plus `lifecycle.py` and `roi.py`. `static/style.css`
was left out. The first lines were:

```text
Review this Flask application for correctness, structure and security. List
concrete problems with file and line. Do not rewrite it.

lifecycle.py and roi.py already existed and were imported, not generated; they
are included so you can check how the app uses them. The specification it was
generated from comes first.
```

**Capture.** The response was read from the rendered page with the code spans
and bold restored, because Gemini's Copy button writes to a clipboard the
in-app browser does not share. The wording is unchanged. Only the list markers
were tidied: each finding is a bullet with its problem nested under it.

---

Here is the review of the provided Flask application for correctness, structure, and security.

### 1. Correctness

- **File `app.py`, Lines 64–71 (`parse_cost`) & Lines 99–100**
  - **Problem:** `parse_cost()` returns `None` if the input string is empty or cannot be converted to a float. However, in `create_action()`, if the user submits an empty or invalid string for `cost_eur` or `cost_hours`, the resulting error message states: "Cost in euros must be a number of zero or more." But HTML5 number inputs or empty submissions send empty strings, which cause `parse_cost` to return `None` even if the user intended to leave it blank (or default to 0). More importantly, the `schema.sql` defines `cost_eur` and `cost_hours` as `NOT NULL DEFAULT 0`, but the code does not fall back to `0` when `parse_cost()` receives an empty value; instead, it pushes `None` into the database execution at line 125 (`(title, description or None, lever, cost_eur, cost_hours)`), which will violate the `NOT NULL` constraint in SQLite and cause a runtime database integrity error.

- **File `app.py`, Lines 135–142 (`show_action`) & `lifecycle.py`, Lines 15–23 (`ALLOWED`)**
  - **Problem:** The routing specification requires showing "buttons for the next legal stages". In `app.py`, `next_stages = sorted(ALLOWED.get(action["status"], frozenset()))` retrieves the allowed next statuses from `lifecycle.py`. However, `lifecycle.py` enforces complex conditional rules via `check_transition()` (such as requiring an owner, lever, hypothesis, expected delta, measurement window, reviewer, and specific actor roles for certain states like `in_review`, `approved`, `rejected`, or `closed`). Because `app.py` never calls `check_transition()`, the UI displays transition buttons for all structural graph paths specified in `ALLOWED`, allowing users to attempt illegal state transitions that will either fail silently or cause unhandled validation exceptions if status changes are enforced elsewhere.

- **File `templates/new.html`, Lines 23 & 27**
  - **Problem:** The default value parameters passed to `form.get('cost_eur', '0')` and `form.get('cost_hours', '0')` only apply if the key is missing from `request.form`. If a user submits empty fields, `request.form` contains empty strings (`""`), meaning `form.get()` returns `""` rather than `'0'`, failing to pre-fill the fields with sensible defaults upon validation failure.

### 2. Structure

- **File `app.py`, Lines 41–45 (`get_db`) & Lines 48–52 (`close_db`)**
  - **Problem:** The application implements the standard Flask pattern for opening a per-request SQLite connection and storing it in `g.db`. However, there is no mechanism or command in `app.py` or a separate initialization script to create the database file and execute `schema.sql` automatically when the application starts or when running locally for the first time, violating the technical constraint ("schema.sql creates the table; app.py does not create tables at import" but leaving out setup instructions or initialization hooks for setting up the SQLite file).

- **File `app.py`, Lines 145–161 (`change_status`)**
  - **Problem:** The status update route performs validation entirely against the static graph (`ALLOWED`) rather than utilizing `lifecycle.py`'s comprehensive validation function (`check_transition`), separating the business logic rules defined in `lifecycle.py` from the actual web application controllers.

### 3. Security

- **File `app.py`, Lines 33–38**
  - **Problem:** The default configuration falls back to `SECRET_KEY=os.environ.get("SECRET_KEY", "dev")`. While acceptable for local development, relying on a hardcoded fallback string like `"dev"` in production environments creates a severe security risk if environment variables fail to load, compromising session cookie signatures and CSRF protection.

- **File `templates/detail.html`, Line 8 & `templates/index.html`, Line 19**
  - **Problem:** Jinja2 automatically escapes variables rendered in templates (e.g., `{{ action.title }}`), preventing stored Cross-Site Scripting (XSS). However, `app.py` performs no server-side sanitization on text inputs (`title`, `description`) beyond length checks. While Jinja2 mitigates direct script execution in standard blocks, ensuring strict length validation and content policies at the database/application layer is critical since descriptions are rendered raw without formatting safeguards.
