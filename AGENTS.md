# Project rules for AI coding agents

This file tells any AI coding agent (Cursor, GitHub Copilot, Gemini CLI, Claude Code and others) how to work on this project. Read it before making changes, and follow it every time.

*Adapted from the Session 5 kit (CCT, 11 November 2026). Three kit rules were
changed to match how this repository already works; each change is marked
**(adapted)**.*

## About this project

- **What the app does, in one or two sentences:** a consulting tool for a small
  (fictional) growth agency, Scaling, that advises several online stores. Every
  growth action is a bounded test with a prediction fixed before it starts, an
  approval, a measured result and a decision; adopted actions become running
  components of the client's growth system, judged on contribution ROI.
- **The main things (entities) the app stores:** users and their roles, clients
  (the stores), plan templates, actions and their history, test assignments,
  components and their monthly results, client reports, and the stores'
  shop data (orders, refunds, sessions, ad spend), plus the events exchanged
  with the Make automations. 18 tables in all.
- **How they connect:** one client has many actions, components, orders,
  sessions and ad-spend rows; one action has many history rows and assignments
  and may become one component; one component has many monthly results; one
  order has many refunds; one user can hold several roles and be assigned to
  several clients.
- **The full data model lives in:** `docs/data-model.md`. Treat it as the source of truth. If the code and that file disagree, stop and ask me.

### Decisions I have made (kept up to date)

| Decision | What I chose | Why |
|---|---|---|
| Deleting a parent row that still has children (every relationship) | RESTRICT; clients and users are deactivated (`is_active = 0`), never deleted | ✍️ *Carlos to write, in business terms* |
| How the schema is applied | `flask --app app init-db` from `schema/002_v2.sql`, not the kit's `migrate.py` (decision 12A, 14 Nov) | ✍️ |
| Password storage | Werkzeug scrypt | ✍️ (recorded in the specification, 28 Oct) |
| Missing costs | stay missing (NULL) and mark a result incomplete; never counted as zero | ✍️ |
| A rejected shop-data batch | frees its `external_id`; only an accepted batch holds it (4 Nov) | ✍️ |
| Where the automations' signing keys live in Make | Team variables (readable in Make), one key per automation with its own permissions, plus the mitigations in `docs/portfolio/automation-strategy.md` (16 Nov, confirmed 17 Nov) | ✍️ |

## Technology

- Python with **Flask** for the web app, **SQLite** for the database. Use SQLite syntax, never MySQL or PostgreSQL syntax (for example `AUTOINCREMENT`, never `AUTO_INCREMENT`).
- Use only Python's built-in `sqlite3` module. Do not add an ORM (such as SQLAlchemy) unless I ask for one.
- Keep things simple enough that a beginner can read them.

## Database rules

1. **(adapted)** **The schema lives in `schema/002_v2.sql`** (`schema/001_initial.sql` is the retired Week 3 slice). It is applied with `flask --app app init-db`. The kit's `tools/migrate.py` is kept for comparison only.
2. **Never edit a migration that has already been applied.** To change the database, add a new numbered file. Never "fix" things by deleting the database.
3. **(adapted)** **Every database connection must run `PRAGMA foreign_keys = ON`.** In this app that one function is `connect()` in `db.py`; every part of the app, the tests and the generator use it. SQLite ignores foreign keys without it.
4. **Only parameterised queries.** Values always go in through `?` placeholders, for example `conn.execute("SELECT * FROM loan WHERE id = ?", (loan_id,))`. Never build SQL with f-strings, `.format()`, `%` or `+`.
5. **Constraints belong in the database:** `NOT NULL` for required fields, `UNIQUE` for things that must never repeat, `CHECK` for allowed values and limits, `FOREIGN KEY` for every relationship.
6. **Never choose an `ON DELETE` behaviour by yourself.** Whether deleting a parent row blocks (`RESTRICT`), deletes its children (`CASCADE`) or empties the link (`SET NULL`) is a business decision. Ask me, then record my answer and the reason in `docs/data-model.md`.
7. **The database is the app's memory.** Do not store app data in Python lists, dictionaries or global variables. Data must still be there after the app is stopped and started again.
8. Database files (`*.db`) are never committed to Git. Make sure `.gitignore` contains `*.db`.

## Web app rules

- If something is asked for that does not exist (for example `/loans/999`), return a **404 Not Found** page, never a crash (500).
- If the database rejects data (a constraint fails), show the user a friendly message and keep them on the form. Do not show a Python error page.
- **No secrets in code.** Passwords, API keys and secret keys come from environment variables (for example `os.environ["SECRET_KEY"]`), never typed into a `.py` file.

## Tests

- **(adapted)** Write tests with **pytest**, as the existing suite does (`python -m pytest`).
- For every constraint, write a test that tries to put **bad data** in and checks it is **rejected**: a duplicate, a value the CHECK rule forbids, a missing required field, a row pointing at something that does not exist, and the delete rule in action.
- Write one test that proves data survives closing and reopening the database file.
- Tests must use a temporary database, never the real `app.db`.

## How to work with me

- Change only what I asked for. Do not rewrite files I did not mention.
- Explain what you did in plain English. I am not a professional developer.
- **At the end of every reply, list any decision you made that I did not specify** (names, types, limits, delete behaviour, libraries, anything). Use the heading "Decisions I made that you did not specify". If there were none, say so.
