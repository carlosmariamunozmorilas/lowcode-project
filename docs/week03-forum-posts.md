# Week 3 · Block A — forum posts

Drafted before the live session of 28 October 2026, for the Block A forum:
the chosen domain for a scope sanity-check, and the three required answers.

These are the pre-session drafts. Every claim is evidenced elsewhere in this
repository — the `127.0.0.1` finding and the dependency pinning come from
[`week02-tool-comparison.md`](week02-tool-comparison.md), the lifecycle and the
exclusion list from [`specification.md`](specification.md). What was actually
posted was rewritten from these in my own words.

---

## Post 0 — chosen domain, for the scope sanity-check

**Domain:** marketing operations — a system of record for marketing work
requests, where the approval trail is enforced by the database rather than
documented in a policy.

**What a user does with it (three things):** raise a request; pick it up as an
owner and work it; review it against a type-specific checklist and approve or
reject it. Every status change writes an append-only transition row, so the
question "who approved this, and were they allowed to?" has an answer.

**Out of scope, deliberately:** no Gantt charts or task dependencies, no time
tracking, no comment threads, no file attachments, no multi-tenancy, no email
sent by the app itself. These are listed in the spec so the generated code does
not quietly acquire them.

**What I would like sanity-checked:** two things.

1. Is a six-state lifecycle with role-based approval the right size for ten
   weeks, or should I cut a state? I have `submitted → assigned → in_review →
   approved / rejected / cancelled`.
2. My rule that the owner who did the work cannot approve it deadlocks in a
   three-person team — nobody is left eligible. Is an admin override that logs
   loudly the normal answer to this, or is the rule itself wrong?

**And one ask:** is there a route through the Industry Engagement Forum to
attach this to a real company's approval process? It would make the Week 12
presentation about something lived rather than something invented.

---

## Answer 1 — why create a branch *before* generating code, not after

Because the branch is what makes the generated code reversible. An agent working
from a specification does not touch one file, it writes twenty at once, and if
that lands directly on `main` there is no boundary left between the state that
worked and the state the model produced. Branch first and the undo is
`git switch main`, costing nothing; branch afterwards and you are picking
generated hunks out of a dirty working tree, guessing which ones you meant to
keep. The practical version for me is next week: Week 3 generates the whole
multi-file application from my spec in one session, and `main` needs to stay the
branch that still passes a clean clone while I find out how much of that output
is actually right.

## Answer 2 — what a pull request is for, if you are the only person on the project

It is the point at which I am forced to read code I would otherwise skim. The
diff view is the difference between accepting twenty generated files and
reviewing them, and reviewing them is the thing Week 8 actually grades — an
authorisation bug is invisible in a running app and obvious in a diff. The PR
description is also the only place the *why* survives: a commit says what
changed, the PR says what I was trying to do and what I decided against, which
is what Week 12 asks me to explain. And it is the hook everything later hangs
on, since tests and security scanners run against a pull request, not against a
push to `main`.

The honest caveat: a solo PR can be a rubber stamp I approve without reading.
What stops that is having something mechanical to pass before merging — for me,
the clean-clone test and, from Week 7, the test suite.

## Answer 3 — two things a specification must state that a one-line request does not

**The runtime environment.** My Week 2 comparison is the evidence: Claude and
Gemini were given the same one-line prompt and both emitted
`app.run(host="127.0.0.1")`, because the prompt never said where the app would
run. That default is correct on a laptop and wrong inside a container in Week 9,
and wrong on the internet in Week 10. Neither tool was at fault — the gap was in
the request, and a specification closes it by stating the bind address, the port
and the fact that this thing eventually lives behind a WSGI server.

**What is excluded.** A one-line request can only add; it has no way of saying
*not this*. Generated code fills silence with plausible features, so a spec that
does not say "no comment threads, no attachments, no time tracking" will get them
eventually, and then they need testing, securing and explaining. The exclusion
list is the cheapest section in my spec and the one that will save the most work.

*(A third, if a third is wanted: who is allowed to do what. A one-liner that says
"add an approve button" produces authentication — are you logged in? — and skips
authorisation — are you allowed to approve *this* request? That is the single
most reliable failure in AI-generated CRUD, and it is why my spec names a role
per route.)*
