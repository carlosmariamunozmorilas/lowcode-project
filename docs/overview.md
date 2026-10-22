# MarketingOps — the application in plain English

A shared workspace where a marketing team requests work, assigns it to someone,
checks it, approves it, and keeps a reliable record of what happened.

This page explains the idea without the technical detail. The precise version —
fields, routes, tests — is in [`specification.md`](specification.md), and the
reasons behind the scope are in [`project-definition.md`](project-definition.md).

---

## The problem

In marketing and agency work, requests arrive from everywhere: an email, a
Slack message, a comment in a meeting. Someone needs a campaign launched, a
landing page checked, a lead followed up. Soon nobody can say who is
responsible, what is still outstanding, or whether anyone actually approved
the result before it went out.

MarketingOps gives every request one place, one owner and one process — and a
history that shows who decided what.

## A request, start to finish

Take a landing page for a paid advertising campaign.

1. **Someone submits a request.** They describe what they need, choose a
   priority and a deadline. The request starts as **submitted**.
2. **A marketing specialist takes it on.** It becomes **assigned**, and
   everyone can see who owns it. It can be reassigned to someone else later.
3. **The owner plans and does the work.** They break it into tasks — check the
   page, test the form, verify the conversion tracking. The work itself happens
   in other tools; MarketingOps records its progress.
4. **The owner sends it for review.** The application refuses while any task
   is still open.
5. **A reviewer checks it against a checklist.** For a landing page that means
   the claims are backed by evidence, brand and disclosure are right, every link
   works, the tracking is in place, and the page is accessible.
6. **The reviewer decides.** Approve it, reject it, or send it back to the owner
   for rework. A request can also be cancelled at any point before a final
   decision.

Every one of those steps adds a line to the request's history: **who acted,
what changed, when, and the note they left.**

## Who uses it

| Person | Their part |
|---|---|
| **Requester** | Explains what is needed and submits it. Can cancel their own requests. |
| **Owner** | Takes responsibility for delivering the work, manages its tasks, sends it to review. |
| **Reviewer** | Checks the work and approves, rejects or returns it. |
| **Administrator** | Manages the system and its users. |

**The rule at the centre of the design:** the person who asked for the work and
the person who did it can never approve it. Approval has to come from someone
independent.

That rule has a known cost. In a three-person team it can leave nobody eligible
to approve. Whether an administrator may make a logged exception, or the rule
should be relaxed, is **still an open decision** — see `specification.md` §10.

## The history is the point

The task list is not what makes this worth building. Plenty of tools track
tasks. What teams usually cannot show is **the approval record**: who approved
this, when, and whether they were allowed to.

So the history is protected. The database refuses any attempt to edit or delete
a history entry; it can only grow. And when the build happens, changing a
request's status and writing its history line must succeed or fail together, so
the current status and the record of how it got there can never disagree.

## The four automations around it

Built in **Make**, a tool that connects services through a sequence of steps.
They form the 40% portfolio and are built across the term, not at the end.

| Automation | In everyday terms | Week |
|---|---|---|
| **Lead intake** | A qualifying lead arrives through an ad form. The automation opens a follow-up request, ready for someone to take on. | 4 |
| **Daily digest** | Every morning, it reads what is still open — who owns it and how long it has waited — and emails a summary. | 5 |
| **Performance alert** | It checks campaign figures against thresholds. If cost per lead crosses the line, it opens a request — or, if one is already open for that metric, adds a task to it instead of raising a second alarm. | 7 |
| **Weekly summary** | It collects the week's figures — approved, rejected, stuck — and asks an AI model to turn those numbers into a readable report. | 11 |

Two rules apply to all four. **They only go through the application's own
API**, never straight into the database: the two that create work send events
in, and the two that report read figures out. And **sending the same thing
twice must not create two requests** — if the same lead arrives twice, the
application recognises it and does nothing the second time.

One more rule for the weekly summary: the AI model sees **only the calculated
numbers**, never the requests themselves. Request titles are typed by people,
and text typed by people should not be fed into a prompt unchecked.

## What the application remembers

Six kinds of record, each a table in the database:

| Record | Holds |
|---|---|
| `users` | the people and their roles |
| `requests` | the work that has been asked for |
| `tasks` | the smaller steps inside each request |
| `review_checks` | the checklist items, and whether each has passed |
| `request_transitions` | the history — every move from one stage to another |
| `automation_events` | what the automations sent in, with the identifiers used to spot duplicates |

Opening a request brings these together on one screen: its owner, its tasks,
its checklist and its history.

## Where the rules come from

The review checklist was not invented for this project. It comes from the
governance layer of my earlier research, the *AI-Era Influence Model*: evidence
for every claim, permitted use of data, audience eligibility, human oversight
of anything automated. Here those principles stop being a framework and become
things the software checks before it lets work through.

## Where AI fits

Two places, and only two. AI helps write and improve the application during
the course — every week's work is generated, reviewed and corrected. And the
weekly summary uses it to explain figures the application has already
calculated. **People remain responsible for approving marketing work.** The
software never approves anything on its own.

## Built with

Python and Flask for the application, SQLite during development and PostgreSQL
in production, Docker for packaging, AWS Lightsail for hosting, GitHub for the
code and its history.

## Where it stands

**Designed, not yet built.** Today the repository holds a starter Flask page,
the lifecycle rules in [`lifecycle.py`](../lifecycle.py), a draft database
schema in [`schema/001_initial.sql`](../schema/001_initial.sql), and the plans.
The connected application is generated from the specification in the Week 3
lab on 28 October 2026, and each week after that adds a layer: the database,
the interface, tests, a security review, packaging, deployment, and governance.

**The finished demonstration** should let someone submit a realistic marketing
request, follow it through its tasks and review, open its approval history, and
watch the automations create work and report on it.
