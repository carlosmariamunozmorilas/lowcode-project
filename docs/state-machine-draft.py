"""Request lifecycle rules for the marketing operations workflow app.

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
    "approved": frozenset(),
    "rejected": frozenset(),
    "cancelled": frozenset(),
}


class TransitionError(Exception):
    """Raised when a transition is not permitted by the lifecycle or by policy."""


@dataclass(frozen=True)
class Request:
    id: int
    status: Status
    requester_id: int
    owner_id: int | None


@dataclass(frozen=True)
class User:
    id: int
    role: str


def check_transition(request: Request, to_status: Status, actor: User) -> None:
    """Validate a proposed status change. Raises TransitionError if refused.

    Three separate gates, deliberately kept separate so each fails its own test:
    the status graph, the ownership requirement, and the approval policy.
    """
    if to_status not in ALLOWED.get(request.status, frozenset()):
        raise TransitionError(f"{request.status} -> {to_status} is not a legal transition")

    if to_status == "in_review" and request.owner_id is None:
        raise TransitionError("a request cannot enter review without an owner")

    # The rule the Week 8 security audit should go looking for.
    if to_status in {"approved", "rejected"}:
        if actor.role not in {"reviewer", "admin"}:
            raise TransitionError(f"role '{actor.role}' may not approve or reject")
        if actor.id == request.requester_id:
            raise TransitionError("a requester may not approve their own request")
        if actor.id == request.owner_id:
            raise TransitionError("the owner who did the work may not approve it")
