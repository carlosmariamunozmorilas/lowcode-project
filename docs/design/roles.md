# Roles and where they are enforced

Brief requirement 3: *at least 2 roles, enforced on the data itself, not only by
hiding buttons or screens.* MarketingOps has five. Hiding a button is never the
control here: the interface hides what a viewer may not do as a courtesy, and
every route re-checks on the server — there are tests that call the routes
directly as the wrong person and expect a refusal.

## The roles

| Role | Who, in a marketing team | Signs in? |
|---|---|---|
| `requester` | Founder, sales, product — asks for marketing work | yes |
| `owner` | Marketing specialist — does the work and records its results | yes |
| `reviewer` | Marketing lead, finance, brand — approves actions and certifies results | yes |
| `admin` | Marketing operations — projects, targets, users | yes |
| `service` | One account per automation, so the record names an actor instead of a blank | **no** — no password; reaches only the two machine routes with a signed request |

On top of the role, **three relationships** decide what a person may do to one
particular action: being its requester, its owner, or its **named reviewer**.

**Several roles per person — decided 28 October 2026, not yet built.** A person
may hold more than one of these roles, and may do what any of them allows. The
approval restriction is applied **by identity, not by role**: nobody reviews,
approves, rejects or closes an action they requested or own, whatever roles they
hold, and `admin` never bypasses it. With no eligible reviewer, the action stays
blocked. `service` is never combined with a human's roles. Today's design still
has one role per user; the schema, `lifecycle.py`, route checks and tests that
change are listed in spec §3, "Multiple roles per user".

**In the hypothetical scenario** ([user-group.md](user-group.md)): the founder
is `admin` + `reviewer`; the ecommerce manager is `requester` + `reviewer`; the
account manager is `requester` + `owner`; the paid media specialist and the
freelance designer/developer are `owner`s. The founder reviews the ecommerce
manager's actions, and the ecommerce manager reviews the founder's.

## What each role can create, read, update and delete

C = create · R = read · U = update · D = delete · — = nothing.
"Own" means the action's requester; "owned" means the action's owner; "named"
means the reviewer named on that action.

| Data | requester | owner | reviewer | admin | service |
|---|---|---|---|---|---|
| **Actions** (`requests`) | C · R · cancel own | R · U owned, until it goes to review | R · approve, reject, close **when named** | C · R · assign · cancel | C (the drift alert opens one) |
| **Action history** (`request_transitions`) | R | R | R | R | — |
| **Tasks** | R | C · R · U on owned actions | R | C · R · U | C (a task on an open drift action) |
| **Review checks** | R | R | R · U **when named** | R · U | — |
| **Projects** | R | R | R | C · R · U | — |
| **KPI targets** | R | R | R | C (a new version) · R | — |
| **KPI measurements** | R | C (a new value or a correction) · R | R | C · R | C (weekly intake) |
| **Users** | R (names) | R (names) | R (names) | C · R · U · deactivate · pseudonymise | — |
| **Automation events, outbound events** | — | — | — | R | C through the API only |

**Nobody deletes anything on the record.** That is not a missing feature: an
action is cancelled, a number is superseded, a user is deactivated. The tables
that hold the record refuse `UPDATE` and `DELETE` at the database level.

## Where each rule is enforced

Four layers, from the outside in. A request that gets past one still meets the
next.

| Layer | What it enforces | Where |
|---|---|---|
| 1 · Sign-in and role | Is this person signed in, and does their role allow this kind of action at all? | `@role_required` on every route (`auth.py`) |
| 2 · The lifecycle rule | May *this* person move *this* action to *that* stage? The named reviewer is neither the requester nor the owner; only the named reviewer signs off; review needs a lever, a hypothesis, the expected change and its window, and a named reviewer; closing needs a result, a confidence label and a decision | `check_transition()` in [`lifecycle.py`](../../lifecycle.py), called by every lifecycle route before it writes — **already written and running** |
| 3 · Fields | Status, `actual_delta` and `confidence` are never read from a general edit form, so an owner cannot post `status=closed` and grade their own work | the lifecycle routes are the only writers of those columns (`routes/request_routes.py`) |
| 4 · The database | An action past `submitted` must have an owner; one in review or beyond must have a named reviewer who is neither its requester nor its owner; a closed action must have its result; history, targets and measurements cannot be edited or deleted | `CHECK` constraints and triggers in [`schema/001_initial.sql`](../../schema/001_initial.sql) — **already written and loading** |

The `service` role is enforced the same way: it has no password, so `/login`
refuses it, and `check_transition()` refuses it any approval or close because
its role is not `reviewer` or `admin`. An automation can open work; it can never
sign work off.

## The tests that prove it

From [`specification.md` §6](../specification.md#6--tests): 3, 4, 5 (wrong
person or wrong role cannot approve), 15 (calling `/approve` directly as the
requester returns 403), 22 (the owner cannot close their own action), 24–27
(the named reviewer rule) and 28 (a service account cannot sign anything off).

## The approval deadlock — decided

In a small team, the rule that the reviewer must be someone other than both the
requester and the owner can leave nobody eligible. **Decided on 28 October
2026:** the rule stays, and such an action **stays blocked**. There is no admin
override, silence never counts as approval, and an overdue decision is reminded
and escalated, never bypassed. The reasoning is argued in the Week 11
governance policy ([`specification.md` §10](../specification.md#10--open-questions-for-the-session-)).

## Still to build

**Several roles per person** — decided, with the implementation work listed in
spec §3. Until it is built, each user holds one role.
