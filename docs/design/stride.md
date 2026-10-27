# Threat analysis — STRIDE

Brief requirement 5: *STRIDE applied to every flow that crosses a trust
boundary, with a mitigation for each threat.* The flows are numbered in
[`dfd.md`](dfd.md); eleven of them cross a boundary, and every one of those
appears below at least once.

The six questions, as the brief puts them: can someone pretend to be someone
else (**S**poofing), change data they should not (**T**ampering), deny an
action (**R**epudiation), see data they should not (**I**nformation
disclosure), stop the service (**D**enial of service), or gain rights they
should not have (**E**levation of privilege)?

**Status** says honestly where each mitigation stands: *in repo* means the code
exists and runs today; otherwise it names the week that builds it and the test
in [`specification.md` §6](../specification.md#6--tests) that proves it. The
column is updated as the term goes on — the brief asks which mitigations were
*actually built and tested*.

| ID | STRIDE | Where | Threat | Mitigation | Status |
|---|---|---|---|---|---|
| T1 | Spoofing | F1 | Someone signs in as a colleague, or raises an action in someone else's name | Passwords hashed (`werkzeug.security`, algorithm checked in Week 8); session cookie `HttpOnly`, `Secure`, `SameSite`; the requester is taken from the session, never from a form field | Week 3–5 · checked Week 8 |
| T2 | Tampering | F1 | An owner posts `status=closed` or `actual_delta=…` in a form and grades their own work (mass assignment) | Status, result and confidence are written only by the lifecycle routes; general edit forms ignore those fields | Week 5 · test 22 |
| T3 | Elevation of privilege | F1 | A requester calls `/requests/<id>/approve` directly, the button being hidden but the route open | `check_transition()` runs server-side on every lifecycle route; role, independence and named-reviewer rules | `lifecycle.py` **in repo** · tests 3–6, 15, 24–28 |
| T4 | Repudiation | F1 | A reviewer approves an action and later denies having done it | Every status change writes a `request_transitions` row with the actor, in the same transaction; triggers make that table append-only | Triggers **in repo** · test 10 |
| T5 | Information disclosure | F1 | Error pages leak stack traces, configuration or SQL | `DEBUG` off outside development; generic error pages; secrets only from the environment | Week 8 · Week 9 config |
| T6 | Denial of service | F1 | Password guessing against `/login` | Rate limit on failed sign-ins per account and address | Week 8 — or recorded as knowingly left ❓ |
| T7 | Information disclosure | F3 | The platform-export sheet is shared too widely and exposes commercial figures | Sheet shared only with the Make connection's account; synthetic figures in this project | Week 4 |
| T8 | Spoofing | F4, F8 | A forged request to `/api/events` records a fake measurement or opens a fake action | HMAC-SHA256 signature over the raw body with a secret from the environment; unsigned or wrongly signed → 401 | Week 4 · test 13 |
| T9 | Tampering | F4, F8 | A replayed or duplicated event records a figure twice | `UNIQUE (source, external_id)`; a redelivery returns 200 and changes nothing | Unique key **in repo** · test 12 |
| T10 | Tampering | F4, F8 | A malicious payload: SQL or HTML in a field, an unknown KPI, a 10,000-character value | Whitelist of fields read; parameterised SQL only; KPI must exist in the fixed tree; length limits; malformed → 400, never 500 | Week 4 · test 14 |
| T11 | Spoofing | F7, F9 | Someone who learns the Make webhook URL sends a forged announcement | Announcements carry ids only; Make reads the true state over a signed call (F8, F10) before acting, so a forged one leads to a read and nothing else; the URL is treated as a secret and rotated if leaked | Weeks 5 and 7 · test 30 |
| T12 | Information disclosure | F7, F9, F11 | Notifications put action content into inboxes, forwards and Slack history | Announcements and messages carry the action number and a link only — never the title, hypothesis or figures (the brief's helpdesk T5) | Weeks 5 and 7 · test 30 |
| T13 | Denial of service | F7, F9 | A loop or a burst of changes uses up Make's 1,000 operations a month | One announcement per change; the drift alert is idempotent per KPI per week; Make's error notifications on; the outbox keeps undelivered events instead of retrying in a tight loop | Weeks 5 and 7 |
| T14 | Spoofing | F11, then F1 | An approval link is forwarded and the wrong person approves (the brief's helpdesk T8) | The link only opens the action; the decision is made signed in, and only the **named reviewer** may approve, reject or close | `lifecycle.py` **in repo** · tests 26–27 |
| T15 | Elevation of privilege | F4, F8, F10, F12 | An automation's credentials are used to approve or close work | Service accounts have no password and cannot sign in; their role is refused every sign-off by `check_transition()`; the machine routes cannot change a status | `lifecycle.py` **in repo** · test 28 |
| T16 | Information disclosure | F10 | The awaiting-review list exposes staff emails to anyone who calls the API | `/api/metrics` requires the signature; it returns only the fields the reminder needs | Week 7 · test 13 |
| T17 | Information disclosure | F13 | Commercial figures or personal data reach the AI provider and are retained | Aggregates only — no names, titles or hypotheses; the provider and its retention terms named in `automation-04.md` | Week 8 |
| T18 | Tampering | F13, F14 | Prompt injection through typed text, or a narrative that turns "correlated" into "drove" | No typed text enters the prompt; the confidence labels are passed in and the prompt requires them; the narrative has no write path back into the application; the report says it was written by an AI from aggregates | Week 8 · written up Week 11 |

## What this table does not cover yet

**The host.** Threats against AWS Lightsail itself — the container, the network,
the account — arrive with deployment in Weeks 9 and 10, and are added then.

**Insiders with admin rights.** An admin can create users and change projects.
That trust is deliberate; the record still shows what every admin did, because
history and figures cannot be edited by anyone.
