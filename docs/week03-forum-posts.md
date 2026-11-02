# Week 3 · Block A — forum posts

Posted on **27 October 2026 at 13:43** to the course's Discussion & Posting
Forum, thread *Output posting*, as one reply ("Re: Output posting") holding both
the domain post and the three required answers. The text below is transcribed
from the forum's notification email.

**How it was written:** drafted with Claude Code and posted essentially
unchanged — not rewritten in my own words. An earlier draft of this file said
the opposite; that was not true, and this version replaces it.

Every claim is evidenced elsewhere in this repository: the bind-address finding
comes from [`week02-tool-comparison.md`](week02-tool-comparison.md), the
workflow and the exclusion list from [`specification.md`](specification.md).

**Since posting:** on 30 October the project moved to v2, a tool for an agency
advising several fictional online stores
([`product-definition-v2.md`](product-definition-v2.md)). The counts in Post 1
describe the v1 design as it stood on 27 October; v2 has 18 tables and four
roles ([`specification-v2.md`](specification-v2.md)). The approval deadlock in
question 2 was decided on 28 October: the action stays blocked and admin has
no bypass.

---

WEEK 3 BLOCK A

## Post 1: your domain

My domain: MarketingOps, ROI for marketing work

What it's for:
An ecommerce marketing team logs each piece of work as an "action" that states
which KPI it should move, by how much, and what it costs in money and people's
hours. Each action is closed with what it actually achieved. The app plans and
measures the return of every action on gross profit (not ROAS), and keeps a
record nobody can quietly rewrite.

What a user does with it:

1. Propose an action: pick the lever (checkout fix, paid campaign, bundles...),
   write the hypothesis and the expected change, and state the cost. Before
   saving, a preview shows the action's own ROI, its break-even point, and what
   it would do to the whole project's ROI.
2. Get it approved by one named reviewer, who can be neither the person who
   asked for it nor the person who does it.
3. Close it with the result: what really changed, how sure we are (holdout,
   before/after or correlated), and whether to scale, hold, redesign or retire
   it. The app shows expected against realised ROI.

Out of scope:
Live ad-platform connections, forecasting or causal attribution, custom
formulas, file attachments, comment threads, multi-tenancy. All data is
invented.

Two questions:

1. This is my own idea rather than one of the brief's twenty. It covers the six
   minimums: 12 related tables; Make automations of all three types (a scheduled
   Monday data intake, a drift alert triggered when a figure lands off target,
   and approval routing to the named reviewer); five roles enforced
   server-side; plus a DFD, a STRIDE table and a GDPR write-up. Is it OK to
   build?
2. The approval rule deadlocks in a three-person team, where nobody may be
   eligible to approve. Is an admin override that is logged loudly the usual
   answer?

## Post 2: the three answers

**1. Why should you create a branch before generating code rather than after?**

Because the branch is what makes generated code reversible. An assistant writes
a dozen files at once, and if they land on main nothing separates what worked
from what the model produced. Branch first and undoing it is one command; branch
afterwards and you are picking generated changes out of a messy working copy. It
also lets you commit the raw scaffold first, which is the honest record of what
the AI produced unaided.

**2. What is a pull request for, if you are the only person on the project?**

It is the point where I am forced to read code I would otherwise skim. An
authorisation bug that is invisible in the running app is obvious in a diff, and
the PR description keeps the why: what I tried and what I knowingly left. It is
also where tests and scanners will run from Week 7. A solo PR can become a
rubber stamp; what stops that is having something to pass before merging, like a
clean-clone test now and the test suite later.

**3. Name two things a specification must state that a one-line request does not.**

Where it runs: in Week 2 I gave three assistants the same one-line prompt, and
two of them bound the app to 127.0.0.1, which fails inside a container, while
Gemini used 0.0.0.0, which exposes a laptop's dev server to everyone on the same
Wi-Fi. What is out of scope: a one-line request can only add, and generated code
fills silence with plausible features that then need testing and securing. The
Session 3 solution sheet makes the same point: the out-of-scope list is the most
useful part of a specification.
