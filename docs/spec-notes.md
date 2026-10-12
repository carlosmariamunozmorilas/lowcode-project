# Marketing operations workflow — specification notes

Working notes for the Week 3 deliverable ("a real multi-file application,
generated from your own specification"). Written 2026-10-11.

---

## 1. How the three automations feed the app

All three POST to **one endpoint**, `POST /api/events`, and land in
`automation_events`. None of them touch the database directly — that boundary is
what keeps the Week 8 audit honest.

```
{ "source": "paid_media", "external_id": "<platform id>", "payload": { ... } }
```

Three rules apply to every automation:

- **Authenticated.** A shared secret in an `X-Signature` header, HMAC over the
  raw body. An open webhook is a finding you gave yourself.
- **Idempotent.** `UNIQUE (source, external_id)` means a redelivered event is a
  no-op. Ad platforms and cron jobs both retry; without this you get duplicates.
- **Untrusted.** The payload is attacker-controlled text. Whitelist the fields
  you read, never interpolate them into SQL or HTML. This is the single most
  likely place the AI will generate an injection.

Each automation runs as a **service user** in `users`, so `requester_id` has a
real foreign key and the audit log reads "paid_media bot assigned…" rather than
showing a null actor.

### 1a. Paid media lead capture (portfolio entry, Week 4)

Google/Meta lead form → Make or n8n → `POST /api/events`.

- `external_id` = the platform's lead id.
- Creates a request, `request_type = 'lead'`, `status = 'submitted'`,
  `priority` from campaign value if present.
- Response time is the point: the request exists before anyone opens a laptop.

> Schema change needed: `requests.request_type` CHECK does not yet include
> `'lead'`. Add it.

### 1b. Performance data flags (portfolio entry, Week 5 or 7)

A scheduled job (GitHub Action on cron) pulls GA4 or a CSV export, compares
metrics to thresholds, and posts only on breach.

- `external_id` = `"{metric}:{date}"` — one alert per metric per day. This is
  what stops alert spam, and it is a design decision worth writing up.
- Rule: if an open request already exists for that metric, append a **task** to
  it instead of opening a second request. Alert fatigue is a workflow bug.

### 1c. AI assistant weekly report (portfolio entry, Week 11)

Reads `request_transitions` for the last seven days — the only table it needs,
which is the payoff of an append-only log.

Computes first, in SQL:

- throughput (requests reaching `approved`)
- median cycle time per stage, from consecutive transition timestamps
- rejection rate
- requests stuck in one status beyond N days

**Then** passes those aggregates to the model for a narrative. Never paste raw
log rows into the prompt: it costs more, it leaks whatever someone typed into a
request title, and a request title is user input — a prompt injection vector.
Say this explicitly in the Week 11 governance policy.

---

## 2. The request model

See `week05-schema.sql`. Decisions worth defending:

- **`status` lives on `requests` and is duplicated in `request_transitions`.**
  Denormalised deliberately for list-view query speed. It can drift, so Week 7
  gets a test asserting the two agree.
- **No `updated_at`.** Derive it from the latest transition; a column that must
  be remembered on every write will eventually not be.
- **No deletes.** `cancelled` is a status. Deleting a request would tear a hole
  in the audit log.
- **`owner_id` is nullable, but constrained** — a `CHECK` prevents an ownerless
  request from being anywhere past `submitted`.

## 3. Task assignment

Two different things, deliberately separated:

| | Meaning |
|---|---|
| `requests.owner_id` | Who is *accountable* for the request. One person. |
| `tasks.assignee_id` | Who does one piece of it. Many people, optional. |

- Assignment is manual, with a default owner per `request_type` as a
  convenience. Round-robin and capacity balancing are out of scope — say so in
  the spec rather than letting the AI invent a scheduler.
- **Invariant worth a Week 7 test:** a request cannot enter `in_review` while it
  has an incomplete task.
- Reassignment is `assigned → assigned` with a different `owner_id`. It is a
  legal transition and it writes an audit row, even though the status did not
  change. Test that explicitly — it is the case a naive implementation drops.
- "My queue" is the only view that matters day to day: open requests I own, plus
  tasks assigned to me, ordered by due date.

## 4. Quality checks in the review stage

Checks are **rows in `review_checks`**, not boolean columns on `requests`. That
means a new check needs no migration, and you get who-checked-it and when for
free.

Required set by request type, suggested starting point:

| `check_key` | Applies to | Asks |
|---|---|---|
| `brief_matched` | all | Does the output answer what was actually requested? |
| `links_resolve` | content, landing_page | Does every link return 200? |
| `tracking_present` | campaign, landing_page | UTMs and conversion tag in place? |
| `accessible` | landing_page | Contrast, alt text, keyboard navigation. |
| `data_sourced` | data | Is every figure traceable to a query or export? |
| `brand_ok` | all | Tone and visual check. |

`accessible` deliberately reuses the Week 6 accessibility work, so that session
feeds the app rather than sitting beside it.

**Invariant worth a Week 7 test:** `in_review → approved` is refused while any
required check for that request type is unpassed.

## 5. Why `approve` is the richest Week 8 target

Authorisation is the thing AI-generated CRUD code gets wrong most reliably,
because the model checks *authentication* (are you logged in?) and forgets
*authorisation* (are you allowed to do this specific thing?). The approve route
concentrates four classic findings in one handler:

1. **IDOR.** `POST /requests/42/approve` — does the handler verify the actor
   against *this* request, or just that a session exists?
2. **Mass assignment.** A form POST containing `status=approved` written
   straight into the model, letting a requester skip the whole workflow.
3. **Client-side-only enforcement.** The Approve button hidden in the template
   for non-reviewers while the route stays open to anyone who curls it. This is
   the most common AI output of the four.
4. **Race condition.** Two reviewers approving simultaneously, producing two
   audit rows and an ambiguous history.

Each is specific, demonstrable with a request you can paste into the report, and
fixable — and `check_transition()` in `week05_state_machine.py` is the test that
proves the fix holds. That is the triage narrative the marking scheme rewards,
as opposed to attaching a raw scanner dump.

## 6. What the Week 12 presentation has to cover

Due 2027-01-13.

- **Live demo at the real URL.** Keep a recorded fallback — the instance may be
  broken, rate-limited or deleted on the night.
- **The security story.** What the scanner reported, what you triaged as real,
  what you dismissed as noise *and why*, what you fixed, what you knowingly
  accepted.
- **What you still cannot explain.** The guide explicitly marks this as
  professional maturity. Name the specific files.
- **The governance policy**, including the owner-cannot-approve deadlock
  decision and the reasoning behind whichever way you went.
- **The automations**, shown feeding the app rather than demoed in isolation.
- **Decisions and their costs.** Why Lightsail over Render, why no Kubernetes,
  what the thing costs to run per month.

> Do not delete the AWS instance when the project is submitted on 6 Jan. Delete
> it after presenting on 13 Jan. Keep the billing alarm on in the meantime.
