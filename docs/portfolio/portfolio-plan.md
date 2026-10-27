# Workflow automation portfolio — the 40%

Plan for the four automations. Re-aimed on 22 October at the ROI layer, and
re-mapped on 27 October to the project brief, which requires **one scheduled
automation, one triggered by an event and one with a human approval step**.
Each one ships as `automation-0N.md` in this folder, in the week shown.

> **"Most people are short on automations at this point."** That is the Week 11 sheet, describing where the class is when the project is due. Week 4 gives you one, and Weeks 5, 7 and 8 each prompt another; treating the portfolio as an end-of-course task is the single biggest cause of lost marks on a course shaped like this.

| # | Automation | Brief type | Trigger | Week |
|---|---|---|---|---|
| 1 | Spend and revenue intake | **Scheduled** | Monday 07:00 | 4 |
| 2 | KPI drift alert | **Triggered by an event** | the application records a measurement | 5 |
| 3 | Approval routing | **Human approval step** | an action is sent to review; a reviewer decides | 7 |
| 4 | Weekly ROI narrative | Scheduled, with an AI step | Monday 10:00 | 8, written up 11 |

**What changed on 27 October, and why.** All four earlier automations ran on a
schedule, so the plan met none of the brief's event-triggered or approval
types. The daily digest is dropped: its two useful lines — what is waiting on
whom, and work approved but never measured — move into the approval reminders
and the weekly narrative. The drift alert now fires when a measurement lands
instead of every Monday. Approval routing is new.

---

## What every entry must contain

From the Week 4 sheet, non-negotiable:

1. **The business problem** — what is done manually, **by whom**, **how often**, **how long it takes**
2. **An architecture diagram** — Mermaid, or a screenshot of the Make scenario
3. **The build** — tools, trigger type, the steps
4. **Prompt strategy** — the actual prompts used for the handler, verbatim
5. **Evidence** — screenshots of it running, in `docs/portfolio/img/`
6. **Three failure answers** — what if it fires twice, what if a step fails halfway, what data crosses a third party and is any of it personal data

The brief adds: **a successful test run of each**, shown in a screenshot.

> ⚠️ **Point 1 has to come from you.** The Week 4 sheet says *"Bring a real one. Contrived scenarios are obvious and they mark badly."* I can design the architecture; the names, frequencies and minutes-per-week are yours, and they are what makes it credible. All four below replace work a RevOps or growth role really does — copying platform numbers, noticing drift, chasing approvals, writing the weekly update.

---

## The shared contract

All four reach the application only through its API. None touches the database, and **none computes ROI or decides anything**: Make moves data and messages, the application does the maths in `roi.py` and enforces the rules in `lifecycle.py`, where both are tested.

| Direction | Route | Used by |
|---|---|---|
| Make → app, write | `POST /api/events` | 1 · intake, 2 · drift alert |
| Make → app, read | `GET /api/metrics` | 2 · drift alert, 3 · approval routing, 4 · narrative |
| App → Make, announce | Make custom webhook | 2 · drift alert, 3 · approval routing |

The writes send:

```json
{ "source": "...", "external_id": "...", "payload": { } }
```

- **Signed** — `X-Signature`, HMAC-SHA256 of the raw body, secret from the environment; the `GET` calls are signed too
- **Idempotent** — `UNIQUE (source, external_id)`; a redelivery returns `200` and changes nothing. Applies to the writes; reading twice changes nothing by definition
- **Untrusted** — the payload is attacker-controlled; whitelist the fields read, never interpolate into SQL or HTML
- **Attributed** — each automation runs as its own `service` user, so the audit log names an actor instead of showing a null. A service user has no password and can never approve or close anything

**Announcements are doorbells, not deliveries.** When the application records a
measurement or an action changes stage, it writes an `outbound_events` row in
the same transaction, then posts it to Make's webhook, signed. The payload is
ids only. Make reads what it needs back over a signed `GET` — so a forged
announcement makes Make read the true state and do nothing, and no content sits
in Make's execution history. If Make is down, the row stays undelivered and
goes out with the next one.

Platform: **Make**. Free tier allows multi-step scenarios and 1,000 operations a month; Zapier's free tier caps at two steps and will not carry automation 1.

**Together they form one loop:** spend arrives (1) → a KPI is off target and an action opens (2) → the owner prepares it and names a reviewer, who is asked to approve (3) → the work is done and the reviewer certifies the result → the Monday report explains the realised ROI (4).

---

## Automation 1 — Spend and revenue intake · *scheduled*
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

**App behaviour:** records a `kpi_measurements` row, `source = 'sheet_import'`, `recorded_by` = the intake service user. If that KPI already has a value for that week, the new row supersedes it; the old one stays. Recording it also writes a `measurement.recorded` announcement — which is what triggers automation 2.

**Fires twice** → same value, same hash, same `external_id`: a no-op. **The interesting case** is a *corrected* value — the platform restated last week's spend. Its hash differs, so it is recorded as a correction rather than silently ignored. Whether that is right is an open decision in the specification.

**Fails halfway** → some KPIs recorded, some not. Re-running is safe: the recorded ones no-op, the missing ones land. That is idempotency doing exactly its job.

**Third-party data** → aggregate business figures — spend, sessions, revenue. Not personal data, but commercially sensitive, and they cross Make's and Google's servers. In this project the figures are synthetic. The honest write-up notes what would change with a real client's numbers: a processing agreement, and where Make stores data.

> **What the Week 4 forum asks:** *"Which step could the visual tool not do on its own?"* The handler: validating the payload, recognising a correction, and refusing a KPI the tree does not contain. That logic lives in the application, generated by the AI and reviewed — which is also where the prompts for point 4 come from.

---

## Automation 2 — KPI drift alert · *triggered by an event*
**Week 5 · 11 November**

**Replaces:** noticing, weeks late, that conversion fell after a release — and then raising it with whoever might own it.

**The event:** the application records a measurement — from automation 1, or typed in by an owner. Not a schedule: a figure entered by hand on a Wednesday is checked on Wednesday. This is also the Week 5 sheet's *"something that reads or writes your new database"*: it does both, through the API.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Webhooks — custom webhook | receives `measurement.recorded`: project, KPI, ISO week, measurement id |
| 2 | HTTP · Make a request | `GET /api/metrics?kpi=…&week=…`, signed — the latest value against its target, and the application's own `off_target` flag |
| 3 | Router — `off_target` only | the other branch ends the run |
| 4 | HTTP · Make a request | `POST /api/events`, `source: performance`, signed |

**The application decides what "off target" means**, in SQL against the latest target version. Make only follows the flag. A threshold kept in a Make router would be untested and invisible to the audit.

**`external_id` = `"{kpi}:{iso_week}"`.** One alert per KPI per week. A correction to the same week's figure fires the webhook again, finds the alert already exists, and changes nothing. This single design choice is what separates a useful alert from a channel everybody mutes by Thursday.

**App behaviour:** opens an action for the drifting KPI, raised by the drift service user, without a lever — the owner has to choose one and write a hypothesis before it can go to review. If a drift action for that KPI is already open, the handler adds a **task** to it instead of opening a second one. Alert fatigue is a workflow bug, not a user problem.

**Fires twice** → the week's `external_id` already exists, so nothing happens.

**Fails halfway** → the webhook arrived but the `POST` failed: Make's error handler records the run, and the next measurement for that KPI re-checks it. The announcement itself stays in the outbox until Make accepts it, so an outage delays an alert instead of losing it.

**Third-party data** → none personal. KPI keys, week numbers and ids.

---

## Automation 3 — Approval routing · *human approval step*
**Week 7 · 25 November**

**Replaces:** chasing sign-off in Slack and in meetings — "can you approve the bundle test?" — with no record of who was asked, when, or who finally said yes.

**Why the decision is not made inside Make.** An approve button in an email is
convenient and forwardable: whoever clicks it approves. The brief's own threat
T8 for the helpdesk example is exactly that, and its mitigation is *assign
approvals to a named approver and record who approved*. So Make routes and
chases the approval; the **named reviewer decides signed in to the
application**, where `check_transition()` confirms they are the reviewer named
on that action and are neither its requester nor its owner. The approval step
is human, enforced on the data, and on the record.

**Scenario A — ask** (event-triggered)

| # | Make module | Does |
|---|---|---|
| 1 | Webhooks — custom webhook | receives `action.in_review`: action id, named reviewer id |
| 2 | HTTP · Make a request | `GET /api/metrics?awaiting_review=…`, signed — the reviewer's email and the action's link |
| 3 | Email or Slack | to the named reviewer: *"Action #42 is waiting for your approval"* and the link — never the title or the figures |

**Scenario B — answer** (event-triggered)

| # | Make module | Does |
|---|---|---|
| 1 | Webhooks — custom webhook | receives `action.decided`: action id, decision |
| 2 | HTTP · Make a request | signed read of the requester's and owner's emails |
| 3 | Email or Slack | tells them the outcome, with the link |

**Scenario C — chase** (scheduled, weekdays 09:00)

| # | Make module | Does |
|---|---|---|
| 1 | Schedule | |
| 2 | HTTP · Make a request | `GET /api/metrics?awaiting_review=…&older_than=48h`, signed |
| 3 | Iterator → Email or Slack | a reminder to each named reviewer still waiting |

**The line worth writing:** the reminders also list approved actions past the end of their measurement window with no result yet. Those are the ones that quietly never get measured — the gap this application exists to close.

**Fires twice** → two identical requests to the reviewer. Annoying, not harmful: the decision is still made once, in the application, and a second approval of the same action is refused because it is no longer in review.

**Fails halfway** → the reviewer was not told: scenario C's next morning run reminds them anyway. Nothing is decided by Make, so nothing can be half-decided.

**Third-party data** → the named reviewer's, requester's and owner's work emails, through Make and the mail provider. Personal data, low risk, internal; the messages carry an action number and a link only.

---

## Automation 4 — Weekly ROI narrative · *scheduled, with an AI step*
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

**Never send raw rows to the model.** Three reasons, and the third is the one that belongs in the governance document: it costs more, it leaks whatever someone typed into a title or a hypothesis, and **user input inside a prompt is an injection vector.** Aggregates are numbers; numbers cannot carry instructions. No names either: who is waiting on whom is automation 3's job, not the AI's.

**The narrative must keep the confidence labels.** A realised ROI resting on a `correlated` result is reported as such. A model left to itself will round "probably helped" up to "drove" — that tendency is worth documenting.

**`external_id` = `"weekly:{iso_week}"`**, kept in a Make data store: this automation never writes to the app, so the app cannot be the one to refuse a duplicate.

**Fires twice** → the data store already has the week, so no second report.

**Fails halfway** → no state is lost; the report regenerates from the record, because the record is the source of truth.

**Third-party data** → aggregates and confidence labels only. They cross the AI provider: say which, and what it may retain.

---

## Evidence to capture, per automation

Capture it while it is on screen. Reconstructing a screenshot in January is how people end up with a thin portfolio.

- [ ] The Make scenario, whole, in one shot
- [ ] A successful run in Make's history — the brief requires one per automation
- [ ] The result visible **in the application** — the measurement, the action, the task, the decision on the timeline
- [ ] A duplicate delivery being refused — the screenshot almost nobody has
- [ ] For automation 1, a correction being recorded alongside the original
- [ ] For automation 3, a wrong person refused when they open the approval link
- [ ] The verbatim prompts used to generate the handler

---

## Schedule

| | Brief type | Built | Written up | Status |
|---|---|---|---|---|
| 1 · Spend and revenue intake | Scheduled | Week 4 | Week 4 | |
| 2 · KPI drift alert | Event-triggered | Week 5 | Week 5–6 | |
| 3 · Approval routing | Human approval | Week 7 | Week 7 | |
| 4 · Weekly ROI narrative | Scheduled, AI | Week 8 / break | Week 11 | |

Four, not three. The brief's minimum is three of the three types; the fourth is the AI one, and the cheapest mark on the course: it reads a record that already exists.
