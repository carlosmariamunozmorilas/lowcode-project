# MarketingOps — the application in plain English

A shared workspace where a marketing team plans its work, gets it approved,
does it, and then records what it actually achieved — so the return on every
euro and every hour is on the record, not in someone's memory.

> Every piece of marketing work has to justify itself, and the record shows
> whether it did.

This page explains the idea without the technical detail. The precise version —
fields, routes, tests — is in [`specification.md`](specification.md), and the
reasons behind the scope are in [`project-definition.md`](project-definition.md).

---

## The problem

Marketing teams are busy, and busy is easy to mistake for effective. Requests
arrive from everywhere, work gets done, campaigns go live — and three months
later nobody can say which of those things paid for itself. The usual report
shows ROAS: revenue divided by ad spend. It looks precise and it misleads,
because it ignores two things that decide whether money was made: the margin on
what was sold, and the hours people spent.

MarketingOps asks a question up front and answers it at the end. Before work
starts: *what is this meant to move, by how much, and what will it cost?* After:
*what did it actually move, how sure are we, and did it pay?*

## One example, start to finish

An online store over one quarter, at 40% margin. Three ideas:

| Idea | What it should move | What it costs |
|---|---|---|
| **A · Remove forced sign-up at checkout** | conversion rate, +0.3 points | 24 hours of a developer's time, no cash |
| **B · A Meta prospecting campaign** | sessions, +8,000 | €5,000 of ads and 10 hours |
| **C · Two product bundles** | average order value, +€3 | €800 and 8 hours |

On ROAS — the number most dashboards show — B looks healthy at 1.92 and C
looks even better at 3.75. A doesn't appear at all: it spent nothing on ads.

Counting margin and people time, the picture flips. A returns **€3.29 for every
€1 invested**. C barely breaks even. B **loses money**. The campaign that looks
fine on the usual report is the one that should not be repeated, and the fix
that never shows up on it is the best thing the team did all quarter.

That reversal is what this application exists to make visible.

## How a piece of work moves through it

Each piece of work is an **action**.

1. **Someone proposes it.** A title, a priority, a deadline. It starts as
   **submitted**.
2. **A specialist takes it on.** It becomes **assigned**, and they choose the
   **lever** it pulls — checkout friction, paid prospecting, bundles — and write
   a **hypothesis**: what should change, by how much, and what it will cost in
   cash and hours.
3. **They break it into tasks and do the work.** The work happens in other
   tools; MarketingOps records its progress.
4. **They send it for review, naming who should approve it.** The application
   refuses while any task is open, if no lever and hypothesis have been given,
   if the expected change and the dates it will be measured over are missing,
   or if the person named is the one who asked for the work or did it. The
   prediction is fixed here, before any result exists, so nobody can write it
   afterwards to fit what happened.
5. **That named reviewer approves it** against a checklist — claims backed by evidence,
   brand and disclosure right, links working, tracking in place — or rejects it,
   or sends it back for rework.
6. **Once its measurement window has passed, it is closed.** The same reviewer records
   what actually changed and **how sure they are**: proven by a holdout test,
   seen before and after, or merely correlated — and **what the team will do
   next**: scale it, hold, redesign it or retire it. The application then
   computes the return it actually delivered, next to the one that was
   expected.

Every step adds a line to the action's history: **who acted, what changed,
when, and the note they left.**

## Before committing to an action

Anyone can fill in the form for an action they are considering and press
**Preview**, without saving anything. The application then shows three things:

- **What the action itself would return** — its ROI, its net gain, and how much
  extra revenue it must bring in just to pay for itself.
- **What it would do to the whole project's return.** An action can make money
  and still lower the project's ROI, because it earns less per euro than the
  project already does. A free-shipping test returning 0.13, in a project
  running at 0.19, brings the project down to 0.18 — worth knowing before
  spending the budget.
- **How far to trust the estimate** — how past actions on the same lever did
  against what they promised: *"checkout fixes have delivered 60% of what
  they expected, over four actions."*

None of this is a prediction. The application cannot know the future; it adds
up the team's own assumptions and sets them against the team's own history.
That is exactly why it also measures what happens afterwards: each closed
action makes the next estimate easier to trust.

## Who uses it

| Person | Their part |
|---|---|
| **Requester** | Proposes work. Can cancel their own. |
| **Owner** | Takes the work on, chooses the lever, writes the hypothesis, does it, records the numbers. |
| **Reviewer** | Approves or rejects the work — and, at the end, certifies its result. |
| **Administrator** | Manages the projects, targets and users. |

**The rule at the centre of the design:** the person who asked for the work and
the person who did it never sign it off — not when it is approved, and not
when its result is recorded. Nobody grades their own homework. And only the
one reviewer named on an action can sign it off, so an approval link that gets
forwarded does not hand the decision to whoever clicks it.

That rule has a cost: in a three-person team it can leave nobody eligible.
Whether an administrator may make a logged exception is **still an open
decision**.

## Where the numbers come from

The return of every action is built from a fixed tree of measures:

- **Revenue** = sessions × conversion rate × average order value
- **Gross profit** = revenue × margin
- **ROI** = (extra gross profit − what was invested) ÷ what was invested

What was invested is **cash plus people's time**. Time is never free here.

Each lever moves exactly one of the three measures at the bottom of the tree,
and the application works out what that change is worth.

## A record that cannot be quietly rewritten

The point is not the task list, and not even the charts. It is that the
numbers can be trusted. So the history of every action, every target and every
weekly measurement can only grow. A target that changes, or a figure that is
corrected, is added as a new entry that replaces the old one — and the old one
stays visible. *Who moved the target after the results came in?* always has an
answer.

And a result is never shown as more certain than it is. A return resting on a
before-and-after comparison is labelled as one.

## The four automations around it

Built in **Make**, a tool that connects services through a sequence of steps.
They form the 40% portfolio and are built across the term, not at the end. The
course brief asks for three kinds — one that runs on a schedule, one that
reacts to an event, and one with a person's approval in it — and these four
cover all three.

| Automation | In everyday terms | Kind | Week |
|---|---|---|---|
| **Spend and revenue intake** | Every Monday, last week's figures from the platforms arrive on their own, instead of being copied into a sheet by hand. | On a schedule | 4 |
| **Drift alert** | The moment a new figure lands off target, it opens an action for someone to take on — or adds to the one already open, rather than raising a second alarm. | Reacts to an event | 5 |
| **Approval routing** | When work is ready for review, the one person named to approve it is asked, reminded if they forget, and everyone hears the outcome. The decision itself is made in the application, by that person. | A person approves | 7 |
| **Weekly ROI report** | An AI turns the week's calculated figures into a readable summary, keeping the certainty labels. | On a schedule | 8–11 |

Four rules apply to all of them. They go **only through the application's own
door**, never straight into its database. **Sending the same thing twice
changes nothing.** **They never do the maths** — the application computes
every return, where it can be tested; the automations only move figures in and
messages out. And **they never decide**: an automation can ask for an approval,
but only the named person, signed in, can give it.

The AI in the weekly report sees **only the calculated numbers**, never the
actions themselves: titles and hypotheses are typed by people, and text typed
by people should not be fed into a prompt unchecked.

## Where the ideas come from

Three places. The return calculation comes from revenue-operations practice:
margin-aware, with people's time counted as a cost — more honest than the
dashboards most marketing teams use. The review checklist comes from the
governance layer of my earlier research, the *AI-Era Influence Model*: evidence
for every claim, permitted use of data, audience eligibility, human oversight.
And the rules around the return — fix the prediction before the result, close
every action with a decision, show the break-even point, never count saved
hours as money — come from my own *ROI AI Influence Model* series. Here all
three stop being frameworks and become things the software checks.

How the influence models started, how they grew into three generations, and
exactly what this application takes from each — and leaves out — is told in
[`influence-models.md`](influence-models.md).

## What it deliberately does not do

It does not connect live to ad platforms, build its own formulas, forecast, or
claim to prove what caused what. Proving cause in marketing is a research
field; this application records what was expected, what happened, and how sure
anyone can be — honestly.

## Built with

Python and Flask for the application, SQLite during development and PostgreSQL
in production, Docker for packaging, AWS Lightsail for hosting, GitHub for the
code and its history. All the data is invented: no real store, no real
customers, no real figures.

## Where it stands

**Designed, and its core rules exist as code.** The lifecycle rules are in
[`lifecycle.py`](../lifecycle.py), the return calculations in
[`roi.py`](../roi.py), and the database design in
[`schema/001_initial.sql`](../schema/001_initial.sql) — all three run, and the
example above comes out exactly as described. The design the course brief asks
for — data model, roles, data flows, threats and data protection — is in
[`design/`](design/README.md). The Week 3 lab on 28 October 2026 generates a
first small slice from the specification, and each week after that adds a
layer: the database, the interface, tests, a security review, packaging,
deployment, and governance.

**The finished demonstration** should let someone propose an action, take it
through review, close it with its real result, and watch the project's return
change — then open the Monday report that explains it.
