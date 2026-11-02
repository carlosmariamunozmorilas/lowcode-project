# v2 code — second-assistant review

**Status:** 2 November 2026. Gemini 3.1 Pro (thinking level High) reviewed the
eight core files of the v2 code at tag `v2-baseline`. Its raw answer, the prompt
and the provenance are in
[`experiments/v2-code-review/gemini-review.md`](../experiments/v2-code-review/gemini-review.md).
Each finding below was checked against the code; triage drafted with Claude
Code. All four proposed fixes were **accepted on 2 November and applied** in the
same pull request, each with a test.

## Summary

Four findings: **2 right**, **2 partly right**, none plainly wrong. Gemini also
found rules 1, 2, 8 and 9, CSRF and SQL injection handled — its one slip there
calls mass assignment "IDOR", which is a different flaw.

The most useful catch is a crash: two copies of the same shop-data batch
arriving at the same moment make the second one fail with an error 500
instead of being recorded as a duplicate. The most instructive is partly
right: Gemini blamed the database rule for something the form handling gets
wrong.

## Findings

| # | Gemini's finding | Verdict | Why |
|---|---|---|---|
| 1 | The "each benefit once" index blocks the second component that shares a benefit key, so its cost and hours cannot be recorded; `stage_summary` would double-count if the index were removed | **Partly right** | The index allows a cost-only row (no benefit), and test 7b proves it — so the database is not the problem. But the form is: `routes/components.py` computes a benefit for every `holdout_kept` or `pilot_estimate` month (line 102), so the second component's month always carries a benefit, hits the index and is refused (line 127). Its cost then cannot be recorded at all. The `stage_summary` double count is hypothetical: with the index in place it cannot happen |
| 2 | Two copies of the same batch arriving at the same time both pass the duplicate check; the second fails on the orders, then `_reject` trips the unique index and the request ends in an error 500 | **Right** | `routes/api.py` checks for a duplicate (line 100), then writes later; nothing stops two requests passing the check together. The second one's `_reject` (lines 122–131) inserts a `rejected` row for an `external_id` that already has an `accepted` one, which the partial unique index refuses, and nothing catches that error. No data is corrupted — the first batch stands — but the response is a crash, not "duplicate". Unlikely with one Make scenario, possible with retries |
| 3 | A component moved back from `retired` keeps its old `retired_on` date | **Right** | `routes/components.py` lines 149–151 keep `retired_on` whenever the new status is not `retired`. Minor, but a reactivated component would show a retirement date |
| 4 | The Growth P&L computes its lines as if missing costs were zero | **Partly right** | The screens never show those numbers: every dependent line is replaced by *incomplete*. But `period_pnl` still returns the zero-assumed figure alongside the flag, and `GET /api/metrics` passes it on, so an automation reading `value` without `incomplete` would get a wrong number |

## Fixes made — all four accepted on 2 November

| # | Fix | Where | Test |
|---|---|---|---|
| A | When another component already carries this benefit key for the month, the month is recorded with cost and hours only (benefit empty) instead of being refused, and the screen says so | `routes/components.py` | `test_review_a_…`: a second component sharing a key records its cost; the first keeps the benefit |
| B | `_reject` catches the unique-index error and records the event as `duplicate`, answering 200 like any redelivery | `routes/api.py` | `test_review_b_…`: a rejection for an already-accepted `external_id` becomes a `duplicate`, not a 500 |
| C | `retired_on` is cleared when a component leaves `retired` | `routes/components.py` | `test_review_c_…`: retire then reactivate leaves `retired_on` empty |
| D | An incomplete line carries no value (`None`) instead of the zero-assumed figure, so the API returns `null` for it; the dashboard is unchanged | `measure.py` (`Line`) | test 29 extended |

One of the new tests was wrong at first: its components had no pilot behind
them, so the app had no benefit to compute and the test failed for the wrong
reason. Fixed by giving them a pilot with customers and an order. 94 tests
pass.

## What this review says

On the specification, Gemini got 3 of 12 findings fully right; here, with the
course context and the rules in the prompt, it got 2 of 4 fully right and none
wrong. All four point at real code, and two would not have been found by the
91 existing tests — they cover the rules, not two requests racing or a second
component sharing a key. This is material for Week 7 ("bugs the AI wrote") and
Week 8 (the security audit).
