# Workflow automation portfolio — the 40%

Plan for the four automations. Each one ships as `automation-0N.md` in this folder, in the week shown.

> **"Most people have two."** That is the Week 11 sheet describing where the class is when the project is due. Weeks 4, 5, 7 and 8 each prompt one; treating the portfolio as an end-of-course task is the single biggest cause of lost marks on a course shaped like this.

---

## What every entry must contain

From the Week 4 brief, non-negotiable:

1. **The business problem** — what is done manually, **by whom**, **how often**, **how long it takes**
2. **An architecture diagram** — Mermaid, or a screenshot of the Make scenario
3. **The build** — tools, trigger type, the steps
4. **Prompt strategy** — the actual prompts used for the handler, verbatim
5. **Evidence** — screenshots of it running, in `docs/portfolio/img/`
6. **Three failure answers** — what if it fires twice, what if a step fails halfway, what data crosses a third party and is any of it personal data

> ⚠️ **Point 1 has to come from you.** The brief says *"Bring a real one. Contrived scenarios are obvious and they mark badly."* I can design the architecture; the names, frequencies and minutes-per-week are yours and they are what makes it credible.

---

## The shared contract

All four reach the application only through its API. None touches the database.

| Automations | Route | Direction |
|---|---|---|
| 1 · Lead intake, 3 · Threshold alert | `POST /api/events` | create work |
| 2 · Daily digest, 4 · Weekly summary | `GET /api/metrics` | read aggregates |

The two that write send:

```json
{ "source": "...", "external_id": "...", "payload": { } }
```

- **Signed** — `X-Signature`, HMAC-SHA256 of the raw body, secret from the environment; the two `GET` calls are signed too
- **Idempotent** — `UNIQUE (source, external_id)`; a redelivery returns `200` and changes nothing. Applies to the two that write; reading twice changes nothing by definition
- **Untrusted** — the payload is attacker-controlled; whitelist the fields read, never interpolate into SQL or HTML
- **Attributed** — each automation runs as its own service user, so the audit log names an actor instead of showing a null

Platform: **Make**. Free tier allows multi-step scenarios and 1,000 operations a month; Zapier's free tier caps at two steps and will not carry automation 1.

---

## Automation 1 — Paid media lead intake
**Week 4 · 4 November**

**Replaces:** lead-form submissions arriving by email or daily CSV; someone reads them, decides which qualify, and creates a follow-up by hand. *(Who, how many a day, how many minutes each — yours to fill.)*

**Why a webhook and not polling:** the entire value is latency. Polling every fifteen minutes adds up to fifteen minutes of delay to a lead whose value decays in the first hour, and burns operations doing nothing while no leads arrive.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Custom webhook | receives the lead payload |
| 2 | Filter | qualifying condition only — not every lead becomes a request |
| 3 | Set variable | builds `external_id` from the platform's lead id |
| 4 | HTTP · Make a request | `POST /api/events`, signed |
| 5 | Error handler route | logs 4xx without retrying |

**App behaviour:** creates a request, `request_type = 'lead'`, `status = 'submitted'`, `requester_id` = the `paid_media` service user, and writes the first transition.

**Fires twice** → `external_id` is the platform's lead id, so the second delivery is a no-op. Ad platforms retry; without this you get duplicate requests and a sales rep calls the same person twice.

**Fails halfway** → Make retries on 5xx. On 4xx it must *not* retry: the payload is malformed and retrying it forever is a loop. Route to the error handler.

**Third-party data — and yes, it is personal data.** Name, email, company and phone are personal data under GDPR. That makes this the richest of the four for Week 11, and the honest write-up has to cover: the lawful basis (the person submitted the form), data minimisation (store only what the request needs, not the whole payload), retention (how long does a lead request live?), and that the data crosses **Make's servers** — a third-party processor, possibly outside the EU. This paragraph is the one that will still matter in January.

---

## Automation 2 — Daily open-request digest
**Week 5 · 11 November**

**Replaces:** opening the tracker each morning, working out what is outstanding and who is sitting on it, and chasing by hand.

This is the one the Week 5 brief requires to read or write the database.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — weekdays 08:00 | |
| 2 | HTTP · Make a request | `GET /api/metrics`, signed |
| 3 | Iterator + Text aggregator | groups open requests by owner and age |
| 4 | Email or Slack | sends the digest |

**Fires twice** → two identical emails. Annoying, not harmful: it writes nothing. No idempotency key needed, and saying *why* none is needed is a better answer than inventing one.

**Fails halfway** → nothing is lost; tomorrow's run covers the same ground.

**Third-party data** → colleagues' names and email addresses. Still personal data, lower risk, internal only.

---

## Automation 3 — Performance threshold alert
**Week 7 · 25 November**

**Replaces:** checking campaign exports for cost or conversion drift and raising it with whoever owns the campaign.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — daily | |
| 2 | Fetch export (Sheets or HTTP) | reads the campaign data |
| 3 | Iterator | per metric |
| 4 | Router — breach branch only | threshold comparison |
| 5 | HTTP · Make a request | `POST /api/events`, signed |

**`external_id` = `"{metric}:{date}"`.** One alert per metric per day. This single design choice is what separates a useful alert from a channel everybody mutes by Thursday.

**The rule worth writing up:** if an open request already exists for that metric, the handler appends a **task** to it instead of opening a second request. Alert fatigue is a workflow bug, not a user problem.

**Fires twice** → the day's `external_id` already exists, so nothing happens.

**Fails halfway** → logged, retried on the next scheduled run. A missed alert is recoverable; a duplicated one trains people to ignore alerts.

**Third-party data** → none. Aggregate campaign metrics, no individuals.

---

## Automation 4 — Weekly audit summary
**Week 8 or the Christmas break · written up Week 11**

**Replaces:** writing the weekly status update by hand from memory and a spreadsheet.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — Monday 09:00 | |
| 2 | HTTP · Make a request | `GET /api/metrics?window=7d`, signed |
| 3 | AI module | turns the aggregates into narrative |
| 4 | Email or Slack | posts the report |

**What the app computes, in SQL, before anything leaves it:** throughput (requests reaching `approved`), median cycle time per stage from consecutive transition timestamps, rejection rate, and requests stuck in one status beyond N days. All four derive from `request_transitions` alone — which is the payoff of having made that table append-only.

**Never send raw log rows to the model.** Three reasons, and the third is the one that belongs in the governance document: it costs more, it leaks whatever someone typed into a request title, and **a request title is user input, so a request title inside a prompt is an injection vector.** Aggregates are numbers; numbers cannot carry instructions.

**`external_id` = `"weekly:{iso_week}"`** — one report per week.

**Fires twice** → same week, no second report.

**Fails halfway** → no state is lost; the report regenerates from the log, because the log is the source of truth.

**Third-party data** → aggregates, plus owner names if the report names who is sitting on what.

---

## Evidence to capture, per automation

Capture it while it is on screen. Reconstructing a screenshot in January is how people end up with a thin portfolio.

- [ ] The Make scenario, whole, in one shot
- [ ] A successful run in Make's history
- [ ] The resulting request visible **in the application**
- [ ] A duplicate delivery being refused — this is the screenshot almost nobody has
- [ ] The verbatim prompts used to generate the handler

---

## Schedule

| | Built | Written up | Status |
|---|---|---|---|
| 1 · Lead intake | Week 4 | Week 4 | |
| 2 · Daily digest | Week 5 | Week 5–6 | |
| 3 · Threshold alert | Week 7 | Week 7 | |
| 4 · Weekly summary | Week 8 / break | Week 11 | |

Four, not three. The brief says 3–4, and the fourth is the cheapest mark on the course: it reads a log that already exists.
