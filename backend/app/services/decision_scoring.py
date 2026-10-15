"""Explainable, bounded priority scoring for generated test cases."""

from __future__ import annotations

from typing import Any


def score_test_case(
    *,
    priority: str | None,
    category: str | None,
    step_count: int,
    severity: str | None = None,
    historical_failure: bool = False,
) -> tuple[int, dict[str, int]]:
    """Return a 0–100 score and the factors used to calculate it.

    Scores intentionally use only supplied test metadata. Request values,
    credentials, and response evidence are never part of the calculation.
    """
    priority_points = {"high": 30, "medium": 20, "low": 10}.get(
        str(priority or "").lower(),
        15,
    )
    risk_source = str(severity or category or "").lower().replace("_", " ")
    risk_points = 25 if any(term in risk_source for term in ("critical", "high", "negative", "security")) else 15 if "edge" in risk_source or "medium" in risk_source else 5
    coverage_gap_points = 15
    historical_failure_points = 15 if historical_failure else 0
    execution_cost_points = max(-10, 10 - max(0, step_count - 3) * 2)
    factors = {
        "priority": priority_points,
        "risk": risk_points,
        "coverage_gap": coverage_gap_points,
        "historical_failure": historical_failure_points,
        "execution_cost": execution_cost_points,
    }
    return max(0, min(100, sum(factors.values()))), factors


def decision_metadata(*, priority: str | None, category: str | None, steps: list[Any]) -> dict[str, Any]:
    """Build the persisted decision metadata for a newly generated UI case."""
    score, factors = score_test_case(
        priority=priority,
        category=category,
        step_count=len(steps),
    )
    return {"decision_score": score, "decision_score_factors": factors}
