# DietPlanService/tests/conftest.py
"""Shared fixtures: a JWT secret override so tests never touch the real
VitroFit.API secret, a token factory, an app TestClient, and a mocked LLM so
no real NVIDIA API call happens during tests.
"""
import os
import sys
import time
import uuid

# Must be set before `auth` is imported anywhere (it reads JWT_SIGNING_KEY at
# module import time), so tests sign/verify with their own throwaway secret.
os.environ.setdefault("JWT_SECRET", "test-secret-not-the-real-one-padded-to-32-bytes-min")
os.environ.setdefault("JWT_ISSUER", "vitrofit-tests")
os.environ.setdefault("JWT_AUDIENCE", "vitrofit-tests")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import main
import agents
import meal_agent
from calculator import calculate_targets


def make_token(user_id: int = 1, role: str = "User") -> str:
    payload = {
        "sub": str(user_id),
        "iss": os.environ["JWT_ISSUER"],
        "aud": os.environ["JWT_AUDIENCE"],
        "exp": int(time.time()) + 3600,
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/role": role,
    }
    return pyjwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


@pytest.fixture
def auth_headers():
    def _headers(user_id: int = 1, role: str = "User"):
        return {"Authorization": f"Bearer {make_token(user_id, role)}"}
    return _headers


@pytest.fixture
def client():
    return TestClient(main.app)


VALID_PREFS = {
    "age": 30,
    "gender": "male",
    "heightCm": 175,
    "weightKg": 80,
    "activityLevel": "moderate",
    "goal": "weight loss",
    "mealFrequency": "3Meals",
    "restrictions": [],
    "dislikes": "",
    "budgetTier": "medium",
    "budgetCustomAmount": None,
    "medicalConditions": [],
    "cookingTime": "moderate",
}


def expected_target_calories(prefs: dict = VALID_PREFS) -> int:
    return calculate_targets(
        gender=prefs["gender"], age=prefs["age"], height_cm=prefs["heightCm"],
        weight_kg=prefs["weightKg"], activity_level=prefs["activityLevel"], goal=prefs["goal"],
    )["totalCalories"]


def make_meals(calories_each: float = 500.0, name: str = "Grilled chicken bowl", count: int = 4) -> list:
    # Macros roughly reconcile with calories (30% protein / 40% carbs / 30% fat by
    # kcal) so validators.py's macro-sanity check doesn't flag these as implausible
    # regardless of what calories_each is set to for a given test.
    protein_g = round(calories_each * 0.30 / 4)
    carbs_g = round(calories_each * 0.40 / 4)
    fat_g = round(calories_each * 0.30 / 9)
    return [
        {
            "type": "meal",
            "label": f"Meal {i + 1}",
            "items": [
                {
                    "name": name,
                    "portion": "1 bowl",
                    "calories": calories_each,
                    "macros": {"protein": protein_g, "carbs": carbs_g, "fat": fat_g},
                }
            ],
        }
        for i in range(count)
    ]


@pytest.fixture
def mock_generate_meals(monkeypatch):
    """Patches the generate_meals reference agents.py actually calls (imported
    by name into that module), so no real NVIDIA API call happens.
    """
    mock = AsyncMock()
    monkeypatch.setattr(agents, "generate_meals", mock)
    return mock
