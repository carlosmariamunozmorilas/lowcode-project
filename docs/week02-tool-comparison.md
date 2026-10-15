# Week 2 — Tool comparison

> Block B deliverable. The brief is explicit: verbatim prompts, scores with
> evidence, and a reasoned choice. "It felt better" is not a reason.

**Feature built:** `/contact` with server-side validation
**Date:** 2026-10-21

---

## The prompt

Pasted verbatim below, identical for every tool. Any difference in output is
therefore a difference in the tool, not in what I asked for.

```
[paste the exact prompt here]
```

---

## Tool A — <name, version/model>

Raw output saved at `experiments/week02/tool-a/`.

| Criterion | Score /5 | Evidence |
|---|---|---|
| Correctness | | |
| Code quality | | |
| Completeness | | |
| Security | | |

**Notes:**

## Tool B — <name, version/model>

Raw output saved at `experiments/week02/tool-b/`.

| Criterion | Score /5 | Evidence |
|---|---|---|
| Correctness | | |
| Code quality | | |
| Completeness | | |
| Security | | |

**Notes:**

---

## The tests I ran against both

The session specifies these. Record what each tool's output actually did.

| Input | Expected | Tool A | Tool B |
|---|---|---|---|
| Empty submission | Rejected, not a 500 | | |
| Invalid email (`notanemail`) | Rejected | | |
| Message containing `<script>alert(1)</script>` | Stored/escaped safely, not executed | | |
| Validation bypassed client-side (curl straight to the route) | **Still rejected** — proves it is server-side | | |

The last row is the one that matters. A tool that only validates in the browser
has not built the feature that was asked for.

---

## Decision

**Chosen:** <tool>

**Why, in terms of the evidence above:**

**What I had to fix in the output before integrating it:**

---

## One surprising difference

For the forum post.
