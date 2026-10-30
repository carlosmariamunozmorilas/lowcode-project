# Workflow automation portfolio — the 40%

Plan for the four automations. Re-aimed on 22 October at the ROI layer,
re-mapped on 27 October to the project brief — which requires **one scheduled
automation, one triggered by an event and one with a human approval step** —
and re-aimed on 30 October at **product v2**: an agency that advises several
online stores and builds growth systems for them
([`product-definition-v2.md`](../product-definition-v2.md)). Each one ships as
`automation-0N.md` in this folder, in the week shown.

> **"Most people are short on automations at this point."** That is the Week 11 sheet, describing where the class is when the project is due. Week 4 gives you one, and Weeks 5, 7 and 8 each prompt another; treating the portfolio as an end-of-course task is the single biggest cause of lost marks on a course shaped like this.

| # | Automation | Brief type | Trigger | Week |
|---|---|---|---|---|
| 1 | Shop data intake | **Scheduled** | daily, 06:00 | 4 |
| 2 | Below-target alert | **Triggered by an event** | the application finishes loading a client's new data | 5 |
| 3 | Approval routing | **Human approval step** | an action is submitted; its named lead decides | 7 |
| 4 | Monthly client report | Scheduled, with a read-only AI step | first working day of the month | 8, written up 11 |

**What changed on 30 October, and why.** v2 serves several client stores, and
every result is calculated from each store's own orders, sessions and ad spend
— fictional data, generated per store. So the intake now loads **shop data per
client** instead of weekly KPI figures; the alert watches **each client's growth
system** against that client's target; approval routing is unchanged in shape,
with v2's names (consultant, lead); and the weekly narrative becomes a
**monthly report per client**, drafted by a read-only AI and reviewed by the
consultant before it goes anywhere.

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

> ⚠️ **Point 1 has to come from you.** The Week 4 sheet says *"Bring a real one. Contrived scenarios are obvious and they mark badly."* I can design the architecture; the names, frequencies and minutes-per-week are yours, and they are what makes it credible. All four replace work an agency account team really does for its clients — exporting and copying each store's figures, noticing when something stops paying, chasing sign-off, writing the monthly client report.

---

## The shared contract

All four reach the application only through its API. None touches the database, and **none computes ROI or decides anything**: Make moves data and messages, the application does the maths in `roi.py` and enforces the rules in `lifecycle.py`, where both are tested.

| Direction | Route | Used by |
|---|---|---|
| Make → app, write | `POST /api/events` | 1 · intake, 2 · alert record |
| Make → app, read | `GET /api/metrics` | 2 · alert, 3 · approval routing, 4 · client report |
| App → Make, announce | Make custom webhook | 2 · alert, 3 · approval routing |

The writes send:

```json
{ "source": "...", "client_id": 1, "external_id": "...", "payload": { } }
```

- **Signed** — `X-Signature`, HMAC-SHA256 of the raw body, secret from the environment; the `GET` calls are signed too
- **Idempotent** — `UNIQUE (source, external_id)`; a redelivery returns `200` and changes nothing. Applies to the writes; reading twice changes nothing by definition
- **Untrusted** — the payload is attacker-controlled; whitelist the fields read, never interpolate into SQL or HTML; a `client_id` that does not exist is refused
- **Attributed** — each automation runs as its own `service` user, so the audit log names an actor instead of showing a null. A service user has no password and can never approve or close anything

**Announcements are doorbells, not deliveries.** When the application finishes
loading data or an action changes stage, it writes an `outbound_events` row in
the same transaction, then posts it to Make's webhook, signed. The payload is
ids only. Make reads what it needs back over a signed `GET` — so a forged
announcement makes Make read the true state and do nothing, and no content sits
in Make's execution history. If Make is down, the row stays undelivered and
goes out with the next one.

Platform: **Make**. Free tier allows multi-step scenarios and 1,000 operations a month; Zapier's free tier caps at two steps and will not carry automation 1. *Operations budget to check in Week 4:* a daily run across three clients must stay inside the free tier — batch rows per request rather than one request per order.

**Together they form one loop:** each client's new data arrives (1) → part of a client's growth system falls below target, and its consultant is told (2) → the consultant proposes an action and its named lead is asked to approve it (3) → the result is measured from the store's own orders, and the monthly report explains the client's system ROI (4).

---

## Automation 1 — Shop data intake · *scheduled*
**Week 4 · 4 November**

**Replaces:** every morning, for each client, exporting yesterday's orders, sessions and ad spend from the store platform, the analytics tool and the ad accounts, and pasting them into each client's reporting sheet by hand. *(Who, which platforms, how many clients, how many minutes — yours to fill.)*

**Where the data comes from:** the client stores are fictional. A generator script writes each store's daily rows into a Google Sheet, one tab per data type, as a store platform's export would. The automation does not know or care that the rows are generated — which is the point: replacing the Sheet with a real export later changes nothing downstream.

**Why a schedule and not a webhook:** the exports are daily batches at a known time, so a schedule is right. This is the opposite of a lead form, where every minute of latency costs money. One run a day is a trivial number of operations — the cost question in the Week 4 forum is worth answering with this contrast.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — daily 06:00 | |
| 2 | Google Sheets — search rows | yesterday's rows, per client: orders, sessions, ad spend |
| 3 | Array aggregator | batches each client's rows into one request per data type |
| 4 | HTTP · Make a request | `POST /api/events`, `source: shop_data`, signed, with `client_id` |
| 5 | Error handler route | logs 4xx without retrying |

**App behaviour:** validates each row and records it in `orders`, `sessions` or `ad_spend` for that client, `recorded_by` = the intake service user. Each row carries its own `external_id` — `"{client}:{type}:{date}:{row id}"` — so a row already loaded is skipped. A refund arrives as its own row pointing at the original order, which stays untouched. When a client's batch is loaded, the application writes a `data.loaded` announcement — which is what triggers automation 2.

**Fires twice** → every row's `external_id` already exists: a no-op.

**Fails halfway** → one client loaded, another not. Re-running is safe: the loaded rows are skipped, the missing ones land. That is idempotency doing exactly its job.

**Third-party data** → order values, costs, channels and session counts — **no customer names, emails or addresses**: the orders are anonymous by design. Commercially sensitive for a real store, and they cross Make's and Google's servers. In this project the figures are synthetic. The honest write-up notes what would change with a real client's data: a processing agreement, and where Make stores data.

> **What the Week 4 forum asks:** *"Which step could the visual tool not do on its own?"* The handler: validating each row, matching a refund to its order, refusing an unknown client or channel, and skipping duplicates. That logic lives in the application, generated by the AI and reviewed — which is also where the prompts for point 4 come from.

---

## Automation 2 — Below-target alert · *triggered by an event*
**Week 5 · 11 November**

**Replaces:** noticing weeks late that a campaign programme or an automation stopped paying for one client, or that a pilot's measurement window ended and nobody read the result.

**The event:** the application finishes loading a client's new data (`data.loaded`, from automation 1). Not a separate schedule: the check runs when there is something new to check.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Webhooks — custom webhook | receives `data.loaded`: client id |
| 2 | HTTP · Make a request | `GET /api/metrics?client=…&alerts=1`, signed — the application's own flags |
| 3 | Router — any flag | the other branch ends the run |
| 4 | HTTP · Make a request | `POST /api/events`, `source: alerts`, signed — the app records the alert and says whether it is new |
| 5 | Email or Slack — new alerts only | to the consultants assigned to that client, with a link |

**The application decides what deserves an alert**, in SQL and `roi.py`: a running component whose month-to-date ROI is below its client's target, or an action whose measurement window has ended without a recorded result. Make only follows the flags. A threshold kept in a Make router would be untested and invisible to the audit.

**`external_id` = `"alert:{client}:{component or action}:{month}"`.** One alert per item per month. A second `data.loaded` the next day finds the alert already recorded and sends nothing. This single design choice is what separates a useful alert from a channel everybody mutes by Thursday.

**Fires twice** → the alert's `external_id` already exists, so no second message.

**Fails halfway** → the alert was recorded but the message failed: Make's error handler records the run, and the alert stays visible on the client's dashboard, where the consultant sees it anyway. The announcement itself stays in the outbox until Make accepts it, so an outage delays an alert instead of losing it.

**Third-party data** → the assigned consultants' work emails; otherwise ids and flags only.

---

## Automation 3 — Approval routing · *human approval step*
**Week 7 · 25 November**

**Replaces:** chasing sign-off by email and in meetings — "can you approve the free-shipping test for Luna Home?" — with no record of who was asked, when, or who finally said yes.

**Why the decision is not made inside Make.** An approve button in an email is
convenient and forwardable: whoever clicks it approves. The brief's own threat
T8 for the helpdesk example is exactly that, and its mitigation is *assign
approvals to a named approver and record who approved*. So Make routes and
chases the approval; the **named lead decides signed in to the application**,
where `check_transition()` confirms they are the reviewer named on that action
and are neither its requester nor its owner. The approval step is human,
enforced on the data, and on the record.

**Scenario A — ask** (event-triggered)

| # | Make module | Does |
|---|---|---|
| 1 | Webhooks — custom webhook | receives `action.in_review`: action id, named lead id |
| 2 | HTTP · Make a request | `GET /api/metrics?awaiting_review=…`, signed — the lead's email and the action's link |
| 3 | Email or Slack | to the named lead: *"Action #42 is waiting for your approval"* and the link — never the client's figures |

**Scenario B — answer** (event-triggered)

| # | Make module | Does |
|---|---|---|
| 1 | Webhooks — custom webhook | receives `action.decided`: action id, decision |
| 2 | HTTP · Make a request | signed read of the proposing consultant's email |
| 3 | Email or Slack | tells them the outcome, with the link |

**Scenario C — chase** (scheduled, weekdays 09:00)

| # | Make module | Does |
|---|---|---|
| 1 | Schedule | |
| 2 | HTTP · Make a request | `GET /api/metrics?awaiting_review=…&older_than=2bd`, signed |
| 3 | Iterator → Email or Slack | a reminder to each named lead still waiting after two business days |

**Fires twice** → two identical requests to the lead. Annoying, not harmful: the decision is still made once, in the application, and a second approval of the same action is refused because it is no longer in review.

**Fails halfway** → the lead was not told: scenario C's next morning run reminds them anyway. Nothing is decided by Make, so nothing can be half-decided.

**Third-party data** → the lead's and consultant's work emails, through Make and the mail provider. Personal data, low risk, internal; the messages carry an action number and a link only.

---

## Automation 4 — Monthly client report · *scheduled, with a read-only AI step*
**Built Week 8 or the Christmas break · written up Week 11**

**Replaces:** writing each client's monthly report by hand, from several dashboards, and usually reporting activity instead of return.

**Scenario**

| # | Make module | Does |
|---|---|---|
| 1 | Schedule — first working day of the month | |
| 2 | HTTP · Make a request | `GET /api/metrics?client=…&month=…`, signed — one client's aggregates |
| 3 | Data store — check | has this client's month already been drafted? |
| 4 | AI module | drafts the report from the aggregates |
| 5 | HTTP · Make a request | `POST /api/events`, `source: report_draft`, signed — the draft is saved **for the consultant to review** |
| 6 | Data store — record | marks the client's month as drafted |

**Nothing goes to a client automatically.** The draft lands in the application,
and the consultant reads, corrects and sends it. The AI drafts; a person
decides what the client is told.

**What the app computes, in SQL and `roi.py`, before anything leaves it:** the client's system ROI against target and by month; each component's cost, contribution and ROI; actions closed this month with their confidence labels; growth KPIs; alerts raised. The model receives those numbers and writes prose around them — it does no arithmetic of its own, following the design in ROI Action Plan 50 (analytics agents).

**Never send raw rows to the model.** Three reasons, and the third is the one that belongs in the governance document: it costs more, it leaks whatever someone typed into a title or a hypothesis, and **user input inside a prompt is an injection vector.** Aggregates are numbers; numbers cannot carry instructions.

**The report must keep the confidence labels.** A result resting on a `before_after` or `correlated` comparison is reported as such. A model left to itself will round "probably helped" up to "drove" — that tendency is worth documenting, and the consultant's review is where it is caught.

**`external_id` = `"report:{client}:{month}"`**, kept in a Make data store and in the application, so a second run drafts nothing.

**Fires twice** → the data store already has that client's month, so no second draft.

**Fails halfway** → no state is lost; the draft regenerates from the record, because the record is the source of truth.

**Third-party data** → one client's aggregates and confidence labels only — no customer data exists to send. They cross the AI provider: say which, and what it may retain.

---

## Evidence to capture, per automation

Capture it while it is on screen. Reconstructing a screenshot in January is how people end up with a thin portfolio.

- [ ] The Make scenario, whole, in one shot
- [ ] A successful run in Make's history — the brief requires one per automation
- [ ] The result visible **in the application** — the loaded orders, the alert, the decision on the timeline, the report draft
- [ ] A duplicate delivery being refused — the screenshot almost nobody has
- [ ] For automation 1, a refund recorded alongside the original order
- [ ] For automation 3, a wrong person refused when they open the approval link
- [ ] For automation 4, the consultant's edits to the AI draft
- [ ] The verbatim prompts used to generate the handler

---

## Schedule

| | Brief type | Built | Written up | Status |
|---|---|---|---|---|
| 1 · Shop data intake | Scheduled | Week 4 | Week 4 | |
| 2 · Below-target alert | Event-triggered | Week 5 | Week 5–6 | |
| 3 · Approval routing | Human approval | Week 7 | Week 7 | |
| 4 · Monthly client report | Scheduled, AI | Week 8 / break | Week 11 | |

Four, not three. The brief's minimum is three of the three types; the fourth is the AI one, and the cheapest mark on the course: it reads a record that already exists.
