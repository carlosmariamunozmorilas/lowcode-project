"""Action lifecycle rules for the growth consultancy tool (spec v2 §5).

An action is a bounded pilot for one client store: it states what it expects to
move and how that will be measured before any result exists, and it is closed
by an independent reviewer with the result it actually produced.

Kept out of the database and out of Flask on purpose: these rules are the most
valuable thing to unit test, and plain functions over frozen dataclasses are far
easier to assert against than routes. Facts that need the database (who may
review for this client, the measured result, guardrail breaches) are passed in
through a Context.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

Status = str

ALLOWED: dict[Status, frozenset[Status]] = {
    "submitted": frozenset({"assigned", "cancelled"}),
    "assigned": frozenset({"in_review", "assigned", "cancelled"}),
    "in_review": frozenset({"approved", "rejected", "assigned", "cancelled"}),
    "approved": frozenset({"closed"}),
    "closed": frozenset(),
    "rejected": frozenset(),
    "cancelled": frozenset(),
}

BENEFIT_TYPES = frozenset({"contribution", "avoided_cost", "enabler"})

# The comparison must match the benefit type (spec v2 §3, decided 2 November).
COMPARISONS_FOR: dict[str, frozenset[str]] = {
    "contribution": frozenset({"holdout", "before_after"}),
    "avoided_cost": frozenset({"invoice"}),
    "enabler": frozenset({"none"}),
}

# The confidence label a closed result carries follows from its comparison.
CONFIDENCE_FOR_COMPARISON: dict[str, str] = {
    "holdout": "holdout",
    "before_after": "before_after",
    "invoice": "documented",
}

CONFIDENCE = frozenset({"holdout", "before_after", "correlated", "documented"})
DECISIONS = frozenset({"adopt", "revise", "reject", "inconclusive"})

# One vocabulary for primary metrics, plan tags and the dashboard (spec v2 §4).
METRICS = frozenset({
    "contribution", "revenue", "orders", "sessions", "conversion",
    "average_order_value", "new_customers", "repeat_rate", "cac", "cpa",
    "refund_rate", "margin_pct", "avoided_cost",
})

LIFECYCLE_STAGES = frozenset({
    "acquisition", "activation", "conversion", "engagement", "retention",
    "repeat", "expansion", "referral", "reactivation", "operations",
})

EARLY_STOP_REASONS = frozenset({
    "data_quality_failure", "technical_failure", "customer_harm",
    "financial_risk", "legal_risk",
})

# Once an action is in review, its prediction cannot change (spec v2 §5).
FROZEN_IN_REVIEW = frozenset({
    "window_start", "window_end", "post_period_days", "expected_benefit_eur",
    "primary_metric", "comparison", "hurdle_eur",
})

# Fields only the workflow writes; a form that posts them is ignored.
WORKFLOW_ONLY = frozenset({
    "status", "measured_benefit_eur", "confidence", "decision", "client_id",
    "requester_id", "created_at", "id",
})

EDITABLE_STATUSES = frozenset({"submitted", "assigned"})

COMPONENT_REVIEW_AFTER_MONTHS = 6


class TransitionError(Exception):
    """Raised when a change is not permitted by the lifecycle or by policy."""


@dataclass(frozen=True)
class User:
    id: int
    roles: frozenset[str] = field(default_factory=frozenset)

    def has(self, role: str) -> bool:
        return role in self.roles


@dataclass(frozen=True)
class Action:
    id: int
    status: Status
    requester_id: int
    benefit_type: str
    owner_id: int | None = None
    reviewer_id: int | None = None
    hypothesis: str | None = None
    primary_metric: str | None = None
    lifecycle_stage: str | None = None
    expected_benefit_eur: float | None = None
    comparison: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    post_period_days: int | None = None
    hurdle_eur: float = 500.0
    measured_benefit_eur: float | None = None
    confidence: str | None = None
    evidence_note: str | None = None
    decision: str | None = None
    decision_note: str | None = None
    early_stop_reason: str | None = None


@dataclass(frozen=True)
class Context:
    """Facts from outside the action that some checks need."""

    today: date
    # Leads assigned to the action's client, active and not service accounts.
    eligible_reviewer_ids: frozenset[int] = frozenset()
    # The action's net benefit after all its costs, when a result exists.
    net_benefit_eur: float | None = None
    guardrail_breached: bool = False
    # A contribution result built on orders with a missing cost.
    result_incomplete: bool = False


def measurement_end(action: Action) -> date | None:
    """Last day of the measurement period: the window plus the post-period."""
    if not action.window_end or action.post_period_days is None:
        return None
    return date.fromisoformat(action.window_end) + timedelta(days=action.post_period_days)


def check_ready_for_review(action: Action, ctx: Context) -> None:
    """Everything spec v2 §5 requires before an action may enter review."""
    if action.owner_id is None:
        raise TransitionError("an action cannot enter review without an owner")
    if not (action.hypothesis or "").strip():
        raise TransitionError("an action cannot enter review without a hypothesis")
    if action.benefit_type not in BENEFIT_TYPES:
        raise TransitionError("an action needs a benefit type")
    if action.benefit_type != "enabler":
        if action.primary_metric not in METRICS:
            raise TransitionError(
                "an action cannot enter review without a primary metric from the vocabulary"
            )
        if action.expected_benefit_eur is None:
            raise TransitionError(
                "an action cannot enter review without its expected benefit"
            )
    if action.lifecycle_stage not in LIFECYCLE_STAGES:
        raise TransitionError("an action cannot enter review without a lifecycle stage")
    if action.comparison not in COMPARISONS_FOR[action.benefit_type]:
        allowed = ", ".join(sorted(COMPARISONS_FOR[action.benefit_type]))
        raise TransitionError(
            f"a {action.benefit_type} action needs the comparison: {allowed}"
        )
    if not (action.window_start and action.window_end):
        raise TransitionError("an action cannot enter review without its measurement window")
    if action.window_end <= action.window_start:
        raise TransitionError("the measurement window must end after it starts")
    if action.post_period_days is None or action.post_period_days < 0:
        raise TransitionError("an action cannot enter review without its post-period")
    if action.reviewer_id is None:
        raise TransitionError("an action cannot enter review without a named reviewer")
    if action.reviewer_id in {action.requester_id, action.owner_id}:
        raise TransitionError("the reviewer must be neither the requester nor the owner")
    if action.reviewer_id not in ctx.eligible_reviewer_ids:
        raise TransitionError(
            "the reviewer must be a lead assigned to this client; "
            "with no eligible reviewer the action stays where it is"
        )


def check_sign_off(action: Action, actor: User) -> None:
    """Approve, reject, send back or close: only the named, independent lead."""
    if actor.has("service"):
        raise TransitionError("an automation may not sign anything off")
    if not actor.has("lead"):
        raise TransitionError("only a lead may approve, reject or close an action")
    # Identity, not role: admin is no exception.
    if actor.id == action.requester_id:
        raise TransitionError("a requester may not sign off their own action")
    if actor.id == action.owner_id:
        raise TransitionError("the owner who did the work may not sign it off")
    if actor.id != action.reviewer_id:
        raise TransitionError("only the reviewer named on this action may sign it off")


def check_close(action: Action, ctx: Context) -> None:
    """What closing needs: the evidence, its label and a decision."""
    end = measurement_end(action)
    early = end is not None and ctx.today <= end
    if early:
        if action.early_stop_reason not in EARLY_STOP_REASONS:
            raise TransitionError(
                f"the measurement period runs until {end.isoformat()}; closing earlier "
                "needs an early-stop reason, and 'the metric looks good' is not one"
            )
        if action.decision == "adopt":
            raise TransitionError("an action stopped early cannot be adopted")

    if action.decision not in DECISIONS:
        raise TransitionError(
            "an action cannot be closed without a decision: adopt, revise, reject or inconclusive"
        )

    if action.benefit_type == "enabler":
        if action.measured_benefit_eur is not None:
            raise TransitionError("an enabler never carries a benefit figure")
        # For an enabler, adopt means its acceptance criterion was met.
        return

    if action.measured_benefit_eur is None:
        raise TransitionError("an action cannot be closed without its measured benefit")
    expected_confidence = CONFIDENCE_FOR_COMPARISON.get(action.comparison or "")
    if action.confidence != expected_confidence:
        raise TransitionError(
            f"a {action.comparison} result is labelled '{expected_confidence}'"
        )
    if action.benefit_type == "avoided_cost" and not (action.evidence_note or "").strip():
        raise TransitionError(
            "an avoided cost needs an evidence note: which invoices show the cost falling"
        )
    if action.benefit_type == "contribution" and ctx.result_incomplete:
        raise TransitionError(
            "the result is built on orders with a missing cost; it is incomplete, not zero"
        )

    if action.decision == "adopt":
        if ctx.net_benefit_eur is None or ctx.net_benefit_eur < action.hurdle_eur:
            raise TransitionError(
                "adopt needs a net benefit at or above the hurdle "
                f"(€{action.hurdle_eur:,.0f})"
            )
        if ctx.guardrail_breached and not (action.decision_note or "").strip():
            raise TransitionError(
                "a guardrail is breached: adopting needs a decision note saying why "
                "the breach is acceptable"
            )


def check_transition(action: Action, to_status: Status, actor: User, ctx: Context) -> None:
    """Validate a proposed status change. Raises TransitionError if refused."""
    if to_status not in ALLOWED.get(action.status, frozenset()):
        raise TransitionError(f"{action.status} -> {to_status} is not a legal transition")
    if actor.has("service"):
        raise TransitionError("an automation may not change an action's stage")

    if to_status == "in_review":
        if actor.id != action.owner_id:
            raise TransitionError("only the owner sends an action to review")
        check_ready_for_review(action, ctx)

    elif action.status == "in_review" and to_status in {"approved", "rejected", "assigned"}:
        check_sign_off(action, actor)

    elif to_status == "closed":
        check_sign_off(action, actor)
        check_close(action, ctx)

    elif to_status == "cancelled":
        if actor.id not in {action.requester_id, action.owner_id} and not actor.has("lead"):
            raise TransitionError("only the requester, the owner or a lead may cancel")

    elif to_status == "assigned":
        if actor.id != action.requester_id and not actor.has("lead"):
            raise TransitionError("only the requester or a lead may assign an action")


def check_edit(action: Action, changed: set[str]) -> None:
    """Fields may change only before review; the prediction is then fixed."""
    blocked = changed & WORKFLOW_ONLY
    if blocked:
        raise TransitionError(f"set only by the workflow: {', '.join(sorted(blocked))}")
    if action.status not in EDITABLE_STATUSES:
        frozen = changed & FROZEN_IN_REVIEW
        if frozen:
            raise TransitionError(
                "the prediction is fixed once the action is in review; cancel it and "
                f"open a new one to change: {', '.join(sorted(frozen))}"
            )
        if changed:
            raise TransitionError("an action can only be edited before review")


def may_record_invoice_month(actor: User, origin: Action | None,
                             eligible_lead_ids: frozenset[int]) -> bool:
    """An invoice month is recorded by an assigned lead independent of the origin action."""
    if not actor.has("lead") or actor.id not in eligible_lead_ids:
        return False
    if origin is not None and actor.id in {origin.requester_id, origin.owner_id}:
        return False
    return True


def component_review_due(measurement: str | None, started_on: str, today: date) -> bool:
    """A pilot estimate is re-tested six months after the component started."""
    if measurement != "pilot_estimate":
        return False
    start = date.fromisoformat(started_on)
    months = (today.year - start.year) * 12 + (today.month - start.month)
    if today.day < start.day:
        months -= 1
    return months >= COMPONENT_REVIEW_AFTER_MONTHS
