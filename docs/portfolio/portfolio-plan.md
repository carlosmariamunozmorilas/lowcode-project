# Workflow automation portfolio — the 40%

Plan for the four automations, re-aimed on 22 October at the ROI layer. Each one ships as `automation-0N.md` in this folder, in the week shown.

> **"Most people are short on automations at this point."** That is the Week 11 sheet, describing where the class is when the project is due. Week 4 gives you one, and Weeks 5, 7 and 8 each prompt another; treating the portfolio as an end-of-course task is the single biggest cause of lost marks on a course shaped like this.

---

## What every entry must contain

From the Week 4 sheet, non-negotiable:

1. **The business problem** — what is done manually, **by whom**, **how often**, **how long it takes**
2. **An architecture diagram** — Mermaid, or a screenshot of the Make scenario
3. **The build** — tools, trigger type, the steps
4. **Prompt strategy** — the actual prompts used for the handler, verbatim
5. **Evidence** — screenshots of it running, in `docs/portfolio/img/`
6. **Three failure answers** — what if it fires twice, what if a step fails halfway, what data crosses a third party and is any of it personal data

> ⚠️ **Point 1 has to come from you.** The Week 4 sheet says *"Bring a real one. Contrived scenarios are obvious and they mark badly."* I can design the architecture; the names, frequencies and minutes-per-week are yours, and they are what makes it credible. All four below replace work a RevOps or growth role really does — copying platform numbers, checking whether KPIs are on track, noticing drift, writing the weekly update.

---

## The shared contract

All four reach the application only through its API. None touches the database, and **none computes ROI**: Make moves data, the application does the maths in `roi.py`, where it is tested.

| Automations | Route | Direction |
|---|---|---|
| 1 · Spend and revenue intake, 3 · KPI drift alert | `POST /api/events` | create something |
| 2 · Daily digest, 3 · KPI drift alert, 4 · Weekly ROI narrative | `GET /api/metrics` | read aggregates |

The two that write send:

```json
{ "source": "...", "external_id": "...", "payload": { } }
```

- **Signed** — `X-Signature`, HMAC-SHA256 of the raw body, secret from the environment; the `GET` calls are signed too
- **Idempotent** — `UNIQUE (source, external_id)`; a redelivery returns `200` and changes nothing. Applies to the writes; reading twice changes nothing by definition
- **Untrusted** — the payload is attacker-controlled; whitelist the fields read, never interpolate into SQL or HTML
- **Attributed** — each automation runs as its own service user, so the audit log names an actor instead of showing a null

Platform: **Make**. Free tier allows multi-step scenarios and 1,000 operations a month; Zapier's free tier caps at two steps and will not carry automation 1.

**Together they form one loop:** spend arrives (1) → the digest shows where things stand (2) → a KPI drifts and an action opens (3) → it is approved, done and closed in the app → the Monday report explains the realised ROI (4).

---

## Automation 1 — Spend and revenue intake
**Week 4 · 4 November**

**Replaces:** every Monday, opening the ad platforms and the shop's analytics, copying last week's spend, sessions, conversion and order value into a reporting sheet by hand. *(Who, which platforms, how many minutes — yours to fill.)*

**Why a schedule and not a webhook:** the data is weekly and arrives at a known time, so a schedule is right. This is the opposite of a lead form, where every minute of latency costs money. Four runs a month is a trivial number of operations — the cost question in the Week 4 forum is worth answering with this contrast.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — Monday 07:00 | |
| 2 | Google Sheets — search rows | reads last ISO week's platform export (synthetic) |
| 3 | Iterator | one bundle per KPI |
| 4 | Set variable | builds `external_id` = `"{kpi}:{iso_week}:{short hash of the value}"` |
| 5 | HTTP · Make a request | `POST /api/events`, `source: spend_revenue`, signed |
| 6 | Error handler route | logs 4xx without retrying |

**App behaviour:** records a `kpi_measurements` row, `source = 'sheet_import'`, `recorded_by` = the intake service user. If that KPI already has a value for that week, the new row supersedes it; the old one stays.

**Fires twice** → same value, same hash, same `external_id`: a no-op. **The interesting case** is a *corrected* value — the platform restated last week's spend. Its hash differs, so it is recorded as a correction rather than silently ignored. Whether that is right is an open decision in the specification.

**Fails halfway** → some KPIs recorded, some not. Re-running is safe: the recorded ones no-op, the missing ones land. That is idempotency doing exactly its job.

**Third-party data** → aggregate business figures — spend, sessions, revenue. Not personal data, but commercially sensitive, and they cross Make's and Google's servers. In this project the figures are synthetic. The honest write-up notes what would change with a real client's numbers: a processing agreement, and where Make stores data.

> **What the Week 4 forum asks:** *"Which step could the visual tool not do on its own?"* The handler: validating the payload, recognising a correction, and refusing a KPI the tree does not contain. That logic lives in the application, generated by the AI and reviewed — which is also where the prompts for point 4 come from.

---

## Automation 2 — Daily digest
**Week 5 · 11 November**

**Replaces:** opening the reporting sheet and the task tracker each morning to work out whether the quarter is on track and what is waiting on whom.

This is the one the Week 5 sheet asks for: *"Something that reads or writes your new database."*

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — weekdays 08:00 | |
| 2 | HTTP · Make a request | `GET /api/metrics`, signed |
| 3 | Text aggregator | KPIs against target; actions waiting for review; approved actions waiting to be closed |
| 4 | Email or Slack | sends the digest |

**The line worth writing:** approved actions that have passed the end of their measurement window and still have no result. Those are the ones that quietly never get measured — the gap this application exists to close.

**Fires twice** → two identical emails. Annoying, not harmful: it writes nothing. No idempotency key needed, and saying *why* none is needed is a better answer than inventing one.

**Fails halfway** → nothing is lost; tomorrow's run covers the same ground.

**Third-party data** → colleagues' names. Personal data, low risk, internal only.

---

## Automation 3 — KPI drift alert
**Week 7 · 25 November**

**Replaces:** noticing, weeks late, that conversion fell after a release — and then raising it with whoever might own it.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — Monday 09:00, after automation 1 | |
| 2 | HTTP · Make a request | `GET /api/metrics`, signed — KPIs against target |
| 3 | Iterator | per KPI |
| 4 | Router — off-target branch only | the threshold comparison |
| 5 | HTTP · Make a request | `POST /api/events`, `source: performance`, signed |

**`external_id` = `"{kpi}:{iso_week}"`.** One alert per KPI per week. This single design choice is what separates a useful alert from a channel everybody mutes by Thursday.

**App behaviour:** opens an action for the drifting KPI, without a lever — the owner has to choose one and write a hypothesis before it can go to review. If a drift action for that KPI is already open, the handler adds a **task** to it instead of opening a second one. Alert fatigue is a workflow bug, not a user problem.

**Fires twice** → the week's `external_id` already exists, so nothing happens.

**Fails halfway** → logged, retried on the next run. A missed alert is recoverable; a duplicated one trains people to ignore alerts.

**Third-party data** → none. Aggregate KPIs, no individuals.

---

## Automation 4 — Weekly ROI narrative
**Built Week 8 or the Christmas break · written up Week 11**

**Replaces:** writing the weekly status update by hand, from memory and a spreadsheet, and usually reporting activity instead of return.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — Monday 10:00 | |
| 2 | HTTP · Make a request | `GET /api/metrics?window=7d`, signed |
| 3 | Data store — check | has this ISO week already been reported? |
| 4 | AI module | turns the aggregates into narrative |
| 5 | Email or Slack | posts the report |
| 6 | Data store — record | marks the week as reported |

**What the app computes, in SQL and `roi.py`, before anything leaves it:** project ROI expected against realised; ROI by lever; actions closed this week with their confidence labels; KPIs against target; actions stuck beyond N days. All of it derives from tables that cannot be rewritten — which is the payoff of having made them append-only.

**Never send raw rows to the model.** Three reasons, and the third is the one that belongs in the governance document: it costs more, it leaks whatever someone typed into a title or a hypothesis, and **user input inside a prompt is an injection vector.** Aggregates are numbers; numbers cannot carry instructions.

**The narrative must keep the confidence labels.** A realised ROI resting on a `correlated` result is reported as such. A model left to itself will round "probably helped" up to "drove" — that tendency is worth documenting.

**`external_id` = `"weekly:{iso_week}"`**, kept in a Make data store: this automation never writes to the app, so the app cannot be the one to refuse a duplicate.

**Fires twice** → the data store already has the week, so no second report.

**Fails halfway** → no state is lost; the report regenerates from the record, because the record is the source of truth.

**Third-party data** → aggregates, plus owner names if the report says who is waiting on what. The aggregates cross the AI provider: say which, and what it may retain.

---

## Evidence to capture, per automation

Capture it while it is on screen. Reconstructing a screenshot in January is how people end up with a thin portfolio.

- [ ] The Make scenario, whole, in one shot
- [ ] A successful run in Make's history
- [ ] The result visible **in the application** — the measurement, the action, the task
- [ ] A duplicate delivery being refused — the screenshot almost nobody has
- [ ] For automation 1, a correction being recorded alongside the original
- [ ] The verbatim prompts used to generate the handler

---

## Schedule

| | Built | Written up | Status |
|---|---|---|---|
| 1 · Spend and revenue intake | Week 4 | Week 4 | |
| 2 · Daily digest | Week 5 | Week 5–6 | |
| 3 · KPI drift alert | Week 7 | Week 7 | |
| 4 · Weekly ROI narrative | Week 8 / break | Week 11 | |

Four, not three. The course asks for 3–4, and the fourth is the cheapest mark on the course: it reads a record that already exists.
