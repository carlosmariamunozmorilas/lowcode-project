"""Return-on-investment formulas for marketing actions.

ROI here is profit-based, not ROAS:

    ROI = (incremental gross profit - investment) / investment

where investment is cash plus people time, and gross profit is revenue times
margin. A campaign can have a healthy ROAS and still lose money; this module is
where that difference is computed, so it is kept free of Flask and the database
and tested directly, like lifecycle.py.

The KPI tree is fixed: revenue = sessions x conversion rate x average order
value. A lever moves exactly one of those three; the revenue it is credited
with holds the other two at their baseline. That is a first-order estimate,
and it ignores interaction between levers on purpose.

What ROI divides by is stated, because the same gain gives a different ratio
over a different denominator: here it is always the full investment of the
action, cash plus people time. Losses are reported as computed; a ratio below
-1 means the action lost more than it cost, and nothing clips it.

Before an action starts, two things help decide whether to run it: what it
would do to the whole project's ROI, and how past actions on the same lever
did against their own expectations. Neither is a forecast; both only restate
the team's assumptions and its own history.
"""

from collections.abc import Iterable
from dataclasses import dataclass

LEAF_KPIS: frozenset[str] = frozenset({"sessions", "conversion_rate", "aov"})


@dataclass(frozen=True)
class Baseline:
    """The three leaf KPIs over one measurement window."""

    sessions: float
    conversion_rate: float
    aov: float


def investment(cost_eur: float, cost_hours: float, hourly_rate: float) -> float:
    """Cash spent plus people time. Time is never free."""
    return cost_eur + cost_hours * hourly_rate


def incremental_revenue(kpi: str, delta: float, baseline: Baseline) -> float:
    """Revenue change from moving one leaf KPI, the other two held at baseline."""
    if kpi == "sessions":
        return delta * baseline.conversion_rate * baseline.aov
    if kpi == "conversion_rate":
        return baseline.sessions * delta * baseline.aov
    if kpi == "aov":
        return baseline.sessions * baseline.conversion_rate * delta
    raise ValueError(f"'{kpi}' is not a leaf KPI; levers move only {sorted(LEAF_KPIS)}")


def incremental_gross_profit(revenue_delta: float, gross_margin: float) -> float:
    """Revenue change times margin."""
    return revenue_delta * gross_margin


def net_gain(gross_profit_delta: float, invested: float) -> float:
    """Profit change minus investment, in euros. Defined even when ROI is not."""
    return gross_profit_delta - invested


def break_even_revenue(invested: float, gross_margin: float) -> float:
    """The extra revenue an action must bring in for its ROI to reach zero."""
    if gross_margin <= 0:
        raise ValueError("gross margin must be above zero")
    return invested / gross_margin


def roi(gross_profit_delta: float, invested: float) -> float | None:
    """Net return per euro invested, or None when nothing was invested.

    None rather than infinity or an error: an action with no cost and no time
    has no meaningful ROI, and the interface should say so.
    """
    if invested == 0:
        return None
    return net_gain(gross_profit_delta, invested) / invested


@dataclass(frozen=True)
class ActionResult:
    """What one action contributes to a project's ROI."""

    gross_profit_delta: float
    invested: float


def project_roi(actions: Iterable[ActionResult]) -> float | None:
    """ROI across a set of actions: total profit change against total investment."""
    actions = list(actions)
    return roi(
        sum(a.gross_profit_delta for a in actions),
        sum(a.invested for a in actions),
    )


@dataclass(frozen=True)
class ProjectImpact:
    """The project's ROI without and with one proposed action."""

    roi_before: float | None
    roi_after: float | None


def project_impact(
    actions: Iterable[ActionResult], proposed: ActionResult
) -> ProjectImpact:
    """What a proposed action would do to the whole project's ROI.

    An action can make money and still lower the project's return, when it earns
    less per euro than the project already does. Seeing that before the work
    starts is the point of the preview.
    """
    actions = list(actions)
    return ProjectImpact(
        roi_before=project_roi(actions),
        roi_after=project_roi([*actions, proposed]),
    )


@dataclass(frozen=True)
class TrackRecord:
    """How closed actions on one lever did against what they expected."""

    closed: int
    realisation: float | None


# --- v2: actions, components and the client's growth system (spec v2 §4) ----
#
# Two economic views, never mixed: an action is judged on full payback (setup
# and operating costs, people time at the client's hourly rate); a running
# component on continuation (its setup is already spent and does not count
# again). Freed hours are capacity and never enter a benefit.


def people_cost(hours: float, hourly_rate: float) -> float:
    return hours * hourly_rate


def action_investment(setup_cost_eur: float, setup_hours: float,
                      operating_cost_eur: float, operating_hours: float,
                      hourly_rate: float) -> float:
    """Everything a pilot cost: cash and people time, setup and operation."""
    return (setup_cost_eur + people_cost(setup_hours, hourly_rate)
            + operating_cost_eur + people_cost(operating_hours, hourly_rate))


def action_net_benefit(measured_benefit_eur: float, invested: float) -> float:
    return measured_benefit_eur - invested


def action_roi(measured_benefit_eur: float, invested: float) -> float | None:
    """Net benefit per euro invested; None when nothing was invested."""
    if invested == 0:
        return None
    return action_net_benefit(measured_benefit_eur, invested) / invested


def component_month_cost(operating_cost_eur: float, operating_hours: float,
                         hourly_rate: float) -> float:
    return operating_cost_eur + people_cost(operating_hours, hourly_rate)


def continuation_roi(benefit_eur: float | None, month_cost: float) -> float | None:
    """A component's monthly ROI: setup excluded. None for an enabler or no cost."""
    if benefit_eur is None or month_cost == 0:
        return None
    return (benefit_eur - month_cost) / month_cost


@dataclass(frozen=True)
class ComponentMonth:
    """One component's month, ready to add up for a client."""

    benefit_key: str | None
    benefit_eur: float | None
    cost_eur: float


@dataclass(frozen=True)
class SystemResult:
    benefit_eur: float
    cost_eur: float
    net_eur: float
    roi: float | None


def system_result(months: Iterable[ComponentMonth]) -> SystemResult:
    """A client's month across its running components, each benefit counted once.

    Two components that contribute to the same outcome share a benefit_key; only
    the first benefit for a key is counted. ROI percentages are never added.
    """
    seen: set[str] = set()
    benefit = 0.0
    cost = 0.0
    for m in months:
        cost += m.cost_eur
        if m.benefit_eur is None:
            continue
        if m.benefit_key is not None:
            if m.benefit_key in seen:
                continue
            seen.add(m.benefit_key)
        benefit += m.benefit_eur
    net = benefit - cost
    return SystemResult(benefit, cost, net, None if cost == 0 else net / cost)


def setup_payback(cumulative_net_eur: float, setup_cost_eur: float) -> float | None:
    """Share of setup already paid back by the components' cumulative net benefit."""
    if setup_cost_eur == 0:
        return None
    return cumulative_net_eur / setup_cost_eur


def track_record(outcomes: Iterable[tuple[float, float]]) -> TrackRecord:
    """Total actual change over total expected change, for one lever.

    Each outcome is (expected_delta, actual_delta) in the lever's own KPI unit,
    which is why a track record is per lever: units cannot be mixed. Totals are
    divided, not ratios averaged, so a small action cannot outweigh a large one.
    None when there is nothing to compare.
    """
    outcomes = list(outcomes)
    expected = sum(e for e, _ in outcomes)
    if not outcomes or expected == 0:
        return TrackRecord(closed=len(outcomes), realisation=None)
    return TrackRecord(
        closed=len(outcomes),
        realisation=sum(a for _, a in outcomes) / expected,
    )
