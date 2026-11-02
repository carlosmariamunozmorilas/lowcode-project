"""Workflow rules (lifecycle.py): spec v2 §11 tests 5, 8, 9, 11, 12, 25, 31–33, 37, 39, 40."""

from dataclasses import replace
from datetime import date

import pytest

from lifecycle import (Action, Context, TransitionError, User, check_edit, check_transition,
                       component_review_due, may_record_invoice_month)

REQUESTER, OWNER, REVIEWER, OTHER_LEAD, ADMIN = 1, 2, 3, 4, 5
TODAY = date(2026, 11, 2)

ready = Action(
    id=1, status="assigned", requester_id=REQUESTER, owner_id=OWNER, reviewer_id=REVIEWER,
    benefit_type="contribution", hypothesis="If x, then y", primary_metric="conversion",
    lifecycle_stage="conversion", expected_benefit_eur=1000, comparison="holdout",
    window_start="2026-09-01", window_end="2026-09-28", post_period_days=14, hurdle_eur=500)
owner = User(OWNER, frozenset({"consultant"}))
reviewer = User(REVIEWER, frozenset({"lead"}))
review_ctx = Context(TODAY, eligible_reviewer_ids=frozenset({REVIEWER, OTHER_LEAD}))


def closing(**changes):
    base = replace(ready, status="approved", measured_benefit_eur=2000, confidence="holdout",
                   decision="adopt")
    return replace(base, **changes)


def test_ready_action_enters_review():
    check_transition(ready, "in_review", owner, review_ctx)


@pytest.mark.parametrize("field", ["owner_id", "hypothesis", "lifecycle_stage", "comparison",
                                   "window_start", "post_period_days", "reviewer_id"])
def test_review_needs_each_required_field(field):
    with pytest.raises(TransitionError):
        check_transition(replace(ready, **{field: None}), "in_review", owner, review_ctx)


def test_25_no_review_without_a_lifecycle_stage():
    with pytest.raises(TransitionError, match="lifecycle stage"):
        check_transition(replace(ready, lifecycle_stage=None), "in_review", owner, review_ctx)


def test_25b_operations_is_a_valid_stage():
    check_transition(replace(ready, lifecycle_stage="operations"), "in_review", owner, review_ctx)


def test_31_no_review_without_a_primary_metric_from_the_vocabulary():
    with pytest.raises(TransitionError, match="primary metric"):
        check_transition(replace(ready, primary_metric="roas"), "in_review", owner, review_ctx)


def test_12_no_eligible_reviewer_means_no_review():
    with pytest.raises(TransitionError, match="lead assigned"):
        check_transition(ready, "in_review", owner, Context(TODAY))


def test_37_comparison_must_match_the_benefit_type():
    with pytest.raises(TransitionError, match="invoice"):
        check_transition(replace(ready, benefit_type="avoided_cost", comparison="holdout"),
                         "in_review", owner, review_ctx)
    enabler = replace(ready, benefit_type="enabler", comparison="none", primary_metric=None,
                      expected_benefit_eur=None)
    check_transition(enabler, "in_review", owner, review_ctx)   # no primary metric needed
    with pytest.raises(TransitionError):
        check_transition(replace(enabler, comparison="holdout"), "in_review", owner, review_ctx)


@pytest.mark.parametrize("person, roles", [
    (REQUESTER, {"lead"}), (OWNER, {"lead"}), (REQUESTER, {"lead", "admin"}),
    (OTHER_LEAD, {"lead"}), (ADMIN, {"admin"}), (REVIEWER, {"consultant"}),
    (REVIEWER, {"service"})])
def test_11_only_the_named_independent_lead_signs_off(person, roles):
    in_review = replace(ready, status="in_review")
    with pytest.raises(TransitionError):
        check_transition(in_review, "approved", User(person, frozenset(roles)), review_ctx)


def test_11b_the_named_lead_may_approve():
    check_transition(replace(ready, status="in_review"), "approved", reviewer, review_ctx)


def test_05_adopt_refused_below_the_hurdle():
    with pytest.raises(TransitionError, match="hurdle"):
        check_transition(closing(), "closed", reviewer, Context(TODAY, net_benefit_eur=499))
    check_transition(closing(), "closed", reviewer, Context(TODAY, net_benefit_eur=500))


def test_08_an_enabler_closes_without_a_benefit():
    enabler = closing(benefit_type="enabler", comparison="none", measured_benefit_eur=None,
                      confidence=None)
    check_transition(enabler, "closed", reviewer, Context(TODAY))
    with pytest.raises(TransitionError, match="never carries"):
        check_transition(replace(enabler, measured_benefit_eur=100), "closed", reviewer,
                         Context(TODAY))


def test_09_avoided_cost_needs_documented_and_evidence():
    avoided = closing(benefit_type="avoided_cost", comparison="invoice", confidence="documented",
                      evidence_note="Invoices for July–September are nil")
    check_transition(avoided, "closed", reviewer, Context(TODAY, net_benefit_eur=600))
    with pytest.raises(TransitionError, match="evidence"):
        check_transition(replace(avoided, evidence_note=" "), "closed", reviewer,
                         Context(TODAY, net_benefit_eur=600))
    with pytest.raises(TransitionError, match="documented"):
        check_transition(replace(avoided, confidence="before_after"), "closed", reviewer,
                         Context(TODAY, net_benefit_eur=600))


def test_32_no_early_close_without_a_reason_and_never_adopt_early():
    early = Context(date(2026, 10, 5), net_benefit_eur=2000)   # period ends 2026-10-12
    with pytest.raises(TransitionError, match="early-stop"):
        check_transition(closing(decision="inconclusive"), "closed", reviewer, early)
    check_transition(closing(decision="inconclusive", early_stop_reason="technical_failure"),
                     "closed", reviewer, early)
    with pytest.raises(TransitionError, match="stopped early"):
        check_transition(closing(early_stop_reason="technical_failure"), "closed", reviewer, early)


def test_33_breached_guardrail_allows_inconclusive_but_adopt_needs_a_note():
    ctx = Context(TODAY, net_benefit_eur=2000, guardrail_breached=True)
    check_transition(closing(decision="inconclusive"), "closed", reviewer, ctx)
    with pytest.raises(TransitionError, match="decision note"):
        check_transition(closing(), "closed", reviewer, ctx)
    check_transition(closing(decision_note="Margin fell by design: bundle pricing"),
                     "closed", reviewer, ctx)


def test_29b_incomplete_result_cannot_close():
    with pytest.raises(TransitionError, match="incomplete"):
        check_transition(closing(), "closed", reviewer,
                         Context(TODAY, net_benefit_eur=2000, result_incomplete=True))


def test_40_prediction_is_fixed_once_in_review():
    check_edit(ready, {"window_end", "hurdle_eur"})                 # before review: fine
    in_review = replace(ready, status="in_review")
    for field in ("window_start", "window_end", "post_period_days", "expected_benefit_eur",
                  "primary_metric", "comparison", "hurdle_eur"):
        with pytest.raises(TransitionError, match="fixed"):
            check_edit(in_review, {field})


def test_15b_workflow_fields_are_never_edited():
    with pytest.raises(TransitionError, match="workflow"):
        check_edit(ready, {"status"})


def test_38b_invoice_month_needs_an_independent_assigned_lead():
    leads = frozenset({REVIEWER, OTHER_LEAD})
    assert may_record_invoice_month(User(OTHER_LEAD, frozenset({"lead"})), ready, leads)
    assert not may_record_invoice_month(User(OWNER, frozenset({"lead"})), ready, leads | {OWNER})
    assert not may_record_invoice_month(User(REQUESTER, frozenset({"lead"})), ready,
                                        leads | {REQUESTER})
    assert not may_record_invoice_month(User(9, frozenset({"consultant"})), ready, leads)


def test_39_pilot_estimate_is_due_for_review_after_six_months():
    assert not component_review_due("pilot_estimate", "2026-05-03", date(2026, 11, 2))
    assert component_review_due("pilot_estimate", "2026-05-02", date(2026, 11, 2))
    assert not component_review_due("holdout_kept", "2026-01-01", date(2026, 11, 2))


def test_service_account_cannot_move_an_action():
    with pytest.raises(TransitionError, match="automation"):
        check_transition(ready, "in_review", User(OWNER, frozenset({"service"})), review_ctx)
