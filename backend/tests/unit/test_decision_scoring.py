from app.services.decision_scoring import score_test_case


def test_score_is_bounded_and_explains_high_risk_case() -> None:
    score, factors = score_test_case(
        priority="high",
        category="negative_test",
        step_count=3,
        historical_failure=True,
    )

    assert score == 95
    assert factors == {
        "priority": 30,
        "risk": 25,
        "coverage_gap": 15,
        "historical_failure": 15,
        "execution_cost": 10,
    }


def test_score_penalizes_longer_low_priority_cases_without_leaving_bounds() -> None:
    score, factors = score_test_case(priority="low", category="happy_path", step_count=50)

    assert score == 20
    assert factors["execution_cost"] == -10
