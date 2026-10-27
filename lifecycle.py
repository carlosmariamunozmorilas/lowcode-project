"""Action lifecycle rules for the marketing operations workflow app.

An action is a marketing request that has to justify itself: it names the KPI
lever it pulls, and it is closed with the result it actually produced.

Kept out of the database on purpose: these rules are the most valuable thing to
unit test in Week 7, and a frozen dict is far easier to assert against than a
table of allowed transitions.
"""

from dataclasses import dataclass

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

# How sure we are that an action caused the change it is credited with.
# The app never presents a before/after comparison as proof.
CONFIDENCE: frozenset[str] = frozenset({"holdout", "before_after", "correlated"})


class TransitionError(Exception):
    """Raised when a transition is not permitted by the lifecycle or by policy."""


@dataclass(frozen=True)
class Request:
    id: int
    status: Status
    requester_id: int
    owner_id: int | None
    lever_id: int | None = None
    hypothesis: str | None = None
    actual_delta: float | None = None
    confidence: str | None = None
    reviewer_id: int | None = None


@dataclass(frozen=True)
class User:
    id: int
    role: str


def check_transition(request: Request, to_status: Status, actor: User) -> None:
    """Validate a proposed status change. Raises TransitionError if refused.

    Separate gates, deliberately kept separate so each fails its own test: the
    status graph, what review needs (including a named reviewer), the approval
    policy, and what closing needs.
    """
    if to_status not in ALLOWED.get(request.status, frozenset()):
        raise TransitionError(
            f"{request.status} -> {to_status} is not a legal transition"
        )

    if to_status == "in_review":
        if request.owner_id is None:
            raise TransitionError("a request cannot enter review without an owner")
        if request.lever_id is None or not (request.hypothesis or "").strip():
            raise TransitionError(
                "an action cannot enter review without a lever and a hypothesis"
            )
        # Named now, so the approval goes to one accountable person and the
        # automation that asks for it knows whom to ask.
        if request.reviewer_id is None:
            raise TransitionError("an action cannot enter review without a reviewer")
        if request.reviewer_id in {request.requester_id, request.owner_id}:
            raise TransitionError(
                "the reviewer must be neither the requester nor the owner"
            )

    # The rule the Week 8 security audit should go looking for. Closing is
    # certifying a result, so it is held to the same independence as approving.
    if to_status in {"approved", "rejected", "closed"}:
        if actor.role not in {"reviewer", "admin"}:
            raise TransitionError(
                f"role '{actor.role}' may not approve, reject or close"
            )
        if actor.id == request.requester_id:
            raise TransitionError("a requester may not sign off their own request")
        if actor.id == request.owner_id:
            raise TransitionError("the owner who did the work may not sign it off")
        # A forwarded approval link must not let someone else decide.
        if actor.id != request.reviewer_id:
            raise TransitionError(
                "only the reviewer named on this action may sign it off"
            )

    if to_status == "closed":
        if request.actual_delta is None:
            raise TransitionError(
                "an action cannot be closed without its actual result"
            )
        if request.confidence not in CONFIDENCE:
            raise TransitionError(
                "an action cannot be closed without a confidence label"
            )
