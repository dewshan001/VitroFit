import pytest
from pydantic import ValidationError

from src.agent.nodes import planner
from src.models.contracts import (
    AnalysisInput,
    ApprovalDecision,
    GymFacts,
    PlannerInput,
    RecommendInput,
    Recommendations,
    Verdict,
)
from tests.support import golden_facts, golden_recs, gym_request


@pytest.mark.parametrize(
    "model,payload",
    [
        (PlannerInput, {"place_id": "p", "name": "n", "surprise": 1}),
        (GymFacts, {"confidence": 0.5, "surprise": 1}),
        (Recommendations, {"workouts": [], "surprise": 1}),
        (Verdict, {"verdict": "pass", "surprise": 1}),
        (ApprovalDecision, {"decision": "approve", "actor_id": "1", "actor_role": "Admin", "surprise": 1}),
    ],
)
def test_contracts_reject_unknown_fields(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_contracts_reject_bad_types_and_ranges():
    with pytest.raises(ValidationError):
        GymFacts(confidence=1.5)
    with pytest.raises(ValidationError):
        ApprovalDecision(decision="maybe", actor_id="1", actor_role="Admin")
    with pytest.raises(ValidationError):
        PlannerInput(place_id="", name="x")


def test_each_agent_input_contract_is_distinct():
    fields = [set(m.model_fields) for m in (PlannerInput, AnalysisInput, RecommendInput)]
    assert len({frozenset(f) for f in fields}) == 3


def test_planner_with_website_plans_scrape_route_and_three_delegated_steps():
    plan = planner.run(gym_request())
    assert plan.route == "scrape"
    assert "scrape_gym_website" in plan.analysis_tools
    assert [s.agent for s in plan.steps] == ["gym_analysis", "workout_recommendation", "validator"]
    assert plan.steps[1].depends_on == ["s1"]


def test_planner_without_website_forbids_scraping():
    plan = planner.run(gym_request(website=None))
    assert plan.route == "search"
    assert "scrape_gym_website" not in plan.analysis_tools


def test_golden_data_is_contract_valid():
    assert golden_facts().confidence == 0.85
    assert len(golden_recs().workouts) == 4
