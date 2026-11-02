# Specification v2 — second-assistant review

**Status:** 2 November 2026. Gemini 3.1 Pro (thinking level High) reviewed
[`specification-v2.md`](specification-v2.md) as merged at commit `43d378f`. Its
raw answer, the prompt and the provenance are in
[`experiments/spec-v2-review/gemini-review.md`](../experiments/spec-v2-review/gemini-review.md).
This page sorts its findings; triage drafted with Claude Code. All six proposed
changes at the end were **accepted on 2 November and applied** to the spec in
the same pull request.

## Summary

Twelve findings: **3 right**, **4 partly right**, **5 wrong or aimed at
something the spec does not say**. The most useful catch is one the earlier
reviews missed: the spec gives each automation its own API secret but never
says how a request tells the app *which* automation it is. The most serious is
one we wrote ourselves: the claim that pseudonymous customer codes are not
personal data.

Most of the wrong findings share one cause: the prompt did not include the
course brief, so Gemini did not know that three automations are a minimum
requirement, or that the append-only triggers were already built and tested.

## Findings

| # | Gemini's finding | Verdict | Why |
|---|---|---|---|
| 1 | No link between the per-automation API secret and the `service` user that `actor_id` / `recorded_by` need | **Right** | §1 and §8 put secrets in config; §3 has service users; nothing maps one to the other |
| 2 | `discount_eur` beside net revenue risks double counting; refunds sit in another table with different dates | **Partly right** | The discount is stored on purpose and tests 1 and 28 guard it. Refund timing is a real gap: the spec does not say which refunds count towards an action's result when they arrive after its measurement period |
| 3 | SQLite `CHECK` cannot hold subqueries, so "reviewer is a lead", "reviewer is assigned to the client" and "report reviewer is a person" cannot be schema rules | **Fact right, target wrong** | The spec never makes them `CHECK`s: §5 says they are enforced in the data-access functions, and tests 14, 21 and 34 cover them |
| 4 | The early-close rule depends on today's date, which a `CHECK` cannot test | **Wrong target** | The spec puts the rule in `lifecycle.py` (§5), with test 32 |
| 5 | Test 18 cannot be written until the request names its automation, so the server knows which secret to use | **Right** | Same root as finding 1 |
| 6 | Test 29 needs more than `SUM()`, which silently skips missing costs | **Partly right** | The test is writable; Gemini is warning about the implementation. A plain `SUM()` is exactly the bug test 29 should catch in AI-generated SQL in Week 7 |
| 7 | Pseudonymised customer codes are still personal data under GDPR Article 4(5) | **Right** | The sentence in §3 ("the only personal data is the team's own user records") is ours, added on 2 November, and it is wrong for a real deployment. In the MVP every customer is fictional, so no real personal data exists, but the design must not claim otherwise |
| 8 | HMAC without a timestamp allows replays | **Partly right** | A replayed event has the same `external_id` and is refused as a duplicate, so it cannot put the app back into an earlier state as Gemini says. A timestamp inside the signature is still good practice and belongs in the Week 8 review |
| 9 | The signed, batched Make intake is scope creep; a CSV upload would do | **Wrong for this course** | The project brief requires at least three automations and the 40% portfolio is built from them; a CSV upload would meet neither |
| 10 | Append-only triggers and `supersedes_id` are too much for an MVP | **Wrong** | The triggers already exist in the v1 schema and were tested on 28 October; they are a few lines and they are the Week 11 audit-logging evidence |
| 11 | The data generator is a project of its own | **Partly right** | It is the biggest hidden cost, as the global review also said; PR #23 already limits past-action history to what the demo needs |
| 12 | Per-customer holdout from raw SQL will be slow and hard to write | **Wrong** | The data is small (Luna Home, the largest store by orders, has about 5,700 orders in six months) and the calculation can run in Python in `measure.py` |

## Changes made — all six accepted on 2 November

| # | Change | Where | From finding |
|---|---|---|---|
| A | Each automation is one `service` user with a unique `automation_name`. A request carries an `X-Automation` header naming it and an `X-Signature` HMAC; the app looks up that automation's secret and records its service user as the actor. Test 18 also refuses a missing or unknown automation name | §2, §3, §6, §8, test 18 | 1, 5 |
| B | The §3 sentence rewritten: in a real deployment `customer_ref` is pseudonymised personal data under GDPR; in the MVP every customer is fictional, so the app holds no real shopper's data. The Week 11 GDPR page treats it as personal data | §3 | 7 |
| C | Added to the Week 8 security surface: a timestamp inside the signature, with old requests refused | §12 | 8 |
| D | An action's result counts the refunds recorded by the end of its measurement period; later refunds never change a closed action. New test 42 | §4, test 42 | 2 |
| E | Note on test 29 that a plain `SUM()` ignoring missing costs is the failure it is meant to catch | §11 | 6 |
| F | Build the generator for Luna Home first, then the other two stores | §9 | 11 |

## What this review says about the reviewer

Gemini 3.1 Pro was far more useful than the signed-out 3.5 Flash-Lite that
reviewed the Week 3 scaffold (two right out of seven). It found a real gap
the earlier reviews of the spec had missed, and a legal error in our own wording. Its
weaker findings came from missing context, not from misreading the text: next
time the review prompt should include the project brief's minimum requirements.
