# BackendAPI/GymAgentService/tests/test_safety.py
import pytest
from fitness_agent.schemas.fitness import HealthInformation
from fitness_agent.agents.safety_agent import SafetyScreeningAgent


def test_safe_user_screening():
    agent = SafetyScreeningAgent()
    info = HealthInformation(
        conditions=["None / Cleared for physical exercise"],
        injuries=None
    )
    result = agent.screen_user(info)
    assert result.status == "SAFE"
    assert result.recommended_action == "CONTINUE"
    assert len(result.risk_flags) == 0


def test_declared_chest_pain_screening():
    agent = SafetyScreeningAgent()
    info = HealthInformation(
        conditions=["Chest pain during exertion / Heart condition"],
        injuries=None
    )
    result = agent.screen_user(info)
    assert result.status == "REVIEW_REQUIRED"
    assert result.recommended_action == "CONTACT_PROFESSIONAL"
    assert len(result.risk_flags) > 0


def test_recent_surgery_limitation():
    agent = SafetyScreeningAgent()
    info = HealthInformation(
        conditions=[],
        injuries="Recent knee surgery 2 weeks ago"
    )
    result = agent.screen_user(info)
    assert result.status == "REVIEW_REQUIRED"
    assert "knee surgery" in result.risk_flags[0]
