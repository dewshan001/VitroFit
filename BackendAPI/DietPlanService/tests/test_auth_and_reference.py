# DietPlanService/tests/test_auth_and_reference.py
import os
import time

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from src.tools.budget_reference import BUDGET_TIERS, resolve_tier
from src.tools.calculator import ACTIVITY_FACTORS, calculate_targets, split_macros
from src.utils import auth
from src.utils.security import _extract_role


def _token(**claims):
    payload = {"sub": "7", "iss": os.environ["JWT_ISSUER"], "aud": os.environ["JWT_AUDIENCE"], "exp": int(time.time()) + 600, **claims}
    return "Bearer " + pyjwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def test_valid_token_gives_the_user_id_and_claims():
    assert auth.get_current_user_id(_token()) == 7
    assert auth.get_current_user_claims(_token(role="Trainer"))["role"] == "Trainer"


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer not.a.jwt"])
def test_missing_or_malformed_headers_are_401(header):
    for fn in (auth.get_current_user_id, auth.get_current_user_claims):
        with pytest.raises(HTTPException) as err:
            fn(header)
        assert err.value.status_code == 401


def test_expired_wrong_audience_and_wrong_signature_are_401():
    expired = _token(exp=int(time.time()) - 10)
    wrong_aud = _token(aud="someone-else")
    forged = "Bearer " + pyjwt.encode({"sub": "1", "iss": os.environ["JWT_ISSUER"], "aud": os.environ["JWT_AUDIENCE"]},
                                      "another-secret-that-is-long-enough-for-hs256-use", algorithm="HS256")
    for header in (expired, wrong_aud, forged):
        with pytest.raises(HTTPException) as err:
            auth.get_current_user_id(header)
        assert err.value.status_code == 401


def test_token_without_a_usable_subject_is_401():
    no_sub = "Bearer " + pyjwt.encode({"iss": os.environ["JWT_ISSUER"], "aud": os.environ["JWT_AUDIENCE"], "exp": int(time.time()) + 60},
                                      os.environ["JWT_SECRET"], algorithm="HS256")
    with pytest.raises(HTTPException) as err:
        auth.get_current_user_id(no_sub)
    assert err.value.status_code == 401 and "sub" in err.value.detail
    with pytest.raises(HTTPException) as err:
        auth.get_current_user_id(_token(sub="not-a-number"))
    assert err.value.status_code == 401


def test_role_is_read_from_either_claim_name():
    assert _extract_role({"role": "Admin"}) == "Admin"
    assert _extract_role({"http://schemas.microsoft.com/ws/2008/06/identity/claims/role": "Trainer"}) == "Trainer"
    assert _extract_role({}) is None


def test_budget_tiers_and_custom_amounts_map_to_reference_pricing():
    assert resolve_tier("low", None) is BUDGET_TIERS["low"]
    assert resolve_tier("unknown", None) is BUDGET_TIERS["medium"]
    for amount, tier in ((1500, "low"), (3000, "medium"), (9000, "high")):
        custom = resolve_tier("custom", amount)
        assert custom["reference_items"] == BUDGET_TIERS[tier]["reference_items"]
        assert custom["label"] == f"Custom (Rs.{amount}/day)"
    assert resolve_tier("custom", None) is BUDGET_TIERS["medium"]


def test_calculator_is_deterministic_and_sensible():
    male = calculate_targets("male", 30, 175, 80, "moderate", "maintenance")
    female = calculate_targets("female", 30, 175, 80, "moderate", "maintenance")
    assert male == calculate_targets("male", 30, 175, 80, "moderate", "maintenance")
    assert male["totalCalories"] > female["totalCalories"]
    assert calculate_targets("male", 30, 175, 80, "moderate", "weight loss")["totalCalories"] < male["totalCalories"]
    assert calculate_targets("male", 30, 175, 80, "moderate", "muscle gain")["totalCalories"] > male["totalCalories"]
    assert set(ACTIVITY_FACTORS) == {"sedentary", "light", "moderate", "active"}
    assert split_macros(2000, "no-such-goal") == split_macros(2000, "maintenance")
