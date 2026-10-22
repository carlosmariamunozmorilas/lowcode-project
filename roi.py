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


def roi(gross_profit_delta: float, invested: float) -> float | None:
    """Net return per euro invested, or None when nothing was invested.

    None rather than infinity or an error: an action with no cost and no time
    has no meaningful ROI, and the interface should say so.
    """
    if invested == 0:
        return None
    return (gross_profit_delta - invested) / invested


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
