# v2 build notes — 2 November 2026

**Status:** built in one session with Claude Code from
[`specification-v2.md`](specification-v2.md), at my request ("do now everything
you can do from spec v2"). Not committed when written; reviewed by me before
merging. This page says what exists, where it departs from the spec, what went
wrong while building it, and what is not built.

**A note for the course.** The course builds one layer a week, with the raw
generated code committed first and a review afterwards. This build ran ahead
of that plan: the schema (Week 5), screens (Week 6) and tests (Week 7) arrived
together, and the first generated version was not committed separately before
the fixes listed below. The weekly evidence for Weeks 5–7 will therefore be a
review of this code rather than a fresh generation.

## What exists

| Piece | Where | Spec |
|---|---|---|
| 18-table schema: `CHECK`s, append-only triggers, "each benefit once" and "one live report per month" indexes, `ON DELETE RESTRICT` everywhere | `schema/002_v2.sql` | §3 |
| Connection per request with `PRAGMA foreign_keys = ON`; `init-db` that refuses to overwrite | `db.py` | §1, §2 |
| Workflow rules: review requirements, comparison by benefit type, frozen prediction, identity sign-off, early close, guardrail note, hurdle, invoice months, review due | `lifecycle.py` | §5 |
| Economics: action payback, continuation ROI, system ROI with each benefit once, setup payback | `roi.py` | §4 |
| Figures from the shop data: order contribution, Growth P&L with *incomplete* lines, holdout and before/after, refund timing, store metrics, guardrails with tolerances, where to grow, quality metrics, component months | `measure.py` | §4 |
| Sign-in (Werkzeug scrypt), roles, client isolation in the data-loading functions, CSRF tokens | `auth.py` | §5, §12 |
| Portfolio, dashboard (main view + Details tab), plans, actions, review queue, components, report review, admin | `routes/`, `templates/` | §6, §7 |
| Signed API: `X-Automation` + `X-Signature`, per-automation scope, all-or-nothing batches with control totals, duplicates recorded | `routes/api.py` | §8 |
| The 72 plan templates with `moves` tags, data fit and store fit | `data/plan_templates.json` | §3, §10 |
| Fictional demo data: three stores, May–October 2026, fixed seed; Luna Home with four closed actions and two components, Brote with plan 20 over four groups, Roble with a pilot in progress | `scripts/generate_shop_data.py` | §9 |
| 90 tests | `tests/` | §11 |

All 23 core tests of §11 and most stretch ones have a counterpart; test names
carry the spec's number (`test_13_…`). The suite also checks that the seeded
history obeys the app's own closing rules.

## Where the build departs from the spec

**Decided 2 November:** 1–7 and 9 accepted and written into the
specification, with a trigger that refuses a component month whose client
differs from its component's (point 3) and a sentence on how a running
component's monthly holdout is counted. Point 8 was settled by reading the six
featured plans (below).

1. **CSRF protection** on every form (a session token, checked before any
   form POST; the signed API is exempt). The spec never named it; the global
   review flagged it as a gap.
2. **`plan_templates.lifecycle_stage`** added, so a new action from a plan gets
   its stage by default.
3. **`component_months.client_id`** added, so the "each benefit once" unique
   index can work per client without a join. Corrections (`supersedes_id`) are
   checked in code, since an index cannot see which row a correction replaces.
4. **`automation_events.event_type`** added, and the `UNIQUE (source,
   external_id)` became a partial unique index that ignores `duplicate` rows,
   so redeliveries are recorded and counted instead of silently dropped.
5. **Refund rate** is orders refunded in the period ÷ orders placed in the
   period, and the guardrails use the same "refunds recorded in the period" rule
   as the Growth P&L. Counting only refunds of the period's own orders made
   every recent period look better than the baseline, because refunds arrive
   days later.
6. **Where to grow, percentages:** conversion and repeat rate use the 5%
   relative tolerance; only margin and refund rate use the point tolerances.
   Two points of conversion would be a huge change for a 1.8% store.
7. **Routes added:** `/actions/<id>/edit` (fields before review) and
   `/admin/clients/<id>/active` (deactivate, never delete).
8. **Plan template values** (window, post-period, hurdle, setup hours) for the
   six featured plans are partly defaults, each marked in
   `data/plan_templates.json` (`values_source`) as "verify against the plan".
   The other 66 use defaults; they cannot start an action.
9. **Fictional names** for the agency team (Ana Ruiz, Marta Gil, Diego Sanz,
   Lucía Vega, Pablo Ortiz) and an ROI target of 0.20 for Brote and Roble.

### Point 8 settled: the six featured plans, read on 2 November

| Plan | Window | Post-period | Setup hours | Hurdle | From the plan |
|---|---|---|---|---|---|
| 03 Discounts | 14 | 14 | 12 | €500 (app default) | 14-day promotion and 14-day post-promotion period; targets are relative (+10% contribution per visitor) |
| 20 Email segmentation | 14 | 0 | 26 | €500 (app default) | 14-day outcome window from the first of two weekly sends; target relative (+10%) |
| 30 Search terms | 42 | 30 | 24 | €500 (app default) | Days 15–56, returns reconciled on Day 87; targets relative (+10% net, 25% ROI) |
| 43 Purchase frequency | 28 | 180 | 40 | €500 (plan) | 28-day enrolment, 180 days of follow-up per customer |
| 50 Analytics agents | 90 | 14 | 64 | €500 (plan) | 90-day supervised operation, invoices reconciled 14 days later |
| 65 Cart recovery | 90 | 44 | 80 | €500 (plan) | 90-day pilot, 14-day purchase window plus 30 days of returns |

Three plans set relative targets rather than a euro hurdle; the app keeps its
€500 default for them and says so in `values_source`. The demo's seeded
pilots are smaller than these defaults (Luna Home's cart pilot ran 28 days,
not 90) — they are the fictional team's own choices, not the template's.
Plan 65 also notes that an email captured at checkout is not, by itself,
permission for a marketing reminder (Irish DPC guidance) — material for the
Week 11 GDPR page.

## What went wrong while building — and was fixed

1. **Seeding order.** The generator linked people to clients before the
   clients existed; the foreign keys refused it on the first run.
2. **The demo broke its own rules.** Two seeded actions were marked "adopt"
   with a net benefit below the €500 hurdle, and two adopted despite a breached
   guardrail without a decision note. The effects and notes were changed, and a
   test now checks every seeded closed action against `lifecycle.check_close`.
3. **Refund lag.** See departure 5: the first guardrail calculation flattered
   recent periods.
4. **A future window shown as a loss.** In the browser, a pilot starting next
   week showed "So far: −€26,346" — an empty future period against the month
   before. The action page now shows no result before the window starts, says
   "partial" before the period ends, and a regression test covers it.
5. **Group counts.** The action page counted customers assigned later to the
   running component as part of the pilot; it now counts the pilot's period only.
6. **A test that could not run.** A parameter named like a fixture
   (`password_hash`) shadowed it; renamed.

## Not built

- **The Make scenarios** — they live in my Make account. The app side (signed
  API, outbox) is built; nothing delivers `outbound_events` yet.
- **The AI report drafting** — needs a model API key and has a cost. The review
  screen, the API to receive a draft and the quality measures are built; the
  demo has no drafts.
- **Docker and deployment** — Weeks 9 and 10.
- **Brote and Roble history** beyond one action each, by the spec's build order.

## Known limits

- The demo's figures are written in by the generator: Luna Home's system ROI of
  over 400% shows that the app measures, not that cart emails work that well.
- A component's monthly holdout counts only that month's new entrants; buyers
  whose order falls in the next month are missed, so month-to-month figures
  are noisy.
- Monthly costs and hours are recorded without independent sign-off; an
  understated cost would inflate ROI (for the Week 11 governance document).
- `SECRET_KEY` is random per run unless set, so a restart signs everyone out.
