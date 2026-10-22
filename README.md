# Marketing operations workflow

A request-tracking application for marketing teams: submit a request, route it
to an owner, review it against a checklist, approve it, and log every
transition so the approval trail is auditable.

**New here?** [`docs/overview.md`](docs/overview.md) explains the whole
application in plain English — a request from start to finish, who does what,
and the four automations around it.

Built for the CCT College Dublin *Certificate in Low-Code, No-Code & AI-Assisted
Application Development* (QQI Level 7, Oct 2026 – Jan 2027).

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

## Status

Week 3, as of 21 October 2026.

- **Week 1** — repository, a minimal Flask application, and the project idea above.
- **Week 2** — Claude and Gemini compared on the same prompt, with the raw
  output kept in `experiments/week02/`. Claude chosen for the main build:
  [`docs/week02-tool-comparison.md`](docs/week02-tool-comparison.md).
- **Week 3** — the specification is drafted in
  [`docs/specification.md`](docs/specification.md); the multi-file application
  is generated from it in the lab on 28 October.

**Known issue.** `requirements.txt` pins Flask 3.1.0 and Werkzeug 3.1.3, which
carry six known advisories (`pip-audit`, 21 October 2026). The upgrade is due
when the Week 3 lab regenerates the dependencies.
