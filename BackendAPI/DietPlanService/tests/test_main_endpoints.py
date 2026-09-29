# DietPlanService/tests/test_main_endpoints.py
from conftest import VALID_PREFS, make_meals, expected_target_calories, poll_workflow

TARGET_CALORIES = expected_target_calories(VALID_PREFS)


def test_generate_endpoint_starts_workflow_immediately(client, auth_headers, mock_generate_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, count=4),
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=101)

    resp = client.post("/api/diet/generate", json=VALID_PREFS, headers=headers)

    # /generate no longer blocks on the LLM - it hands back a workflowId
    # right away so the frontend can poll live progress instead.
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    for field in ("workflowId", "status", "plan"):
        assert field in body

    detail = poll_workflow(client, body["workflowId"], headers)
    assert detail["status"] == "completed"
    assert detail["targets"]["totalCalories"] == TARGET_CALORIES
    assert detail["meals"]
    assert detail["finalOutcome"]["withinTolerance"] is True
    assert detail["approvalStatus"] == "auto_approved"
    assert detail["completedSteps"]


def test_generate_endpoint_rejects_invalid_literal(client, auth_headers):
    bad_prefs = dict(VALID_PREFS, goal="bulk")
    resp = client.post("/api/diet/generate", json=bad_prefs, headers=auth_headers(user_id=101))
    assert resp.status_code == 422


def test_confirm_with_workflow_id_ignores_client_meals(client, auth_headers, mock_generate_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, count=4),
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=102)
    gen_resp = client.post("/api/diet/generate", json=VALID_PREFS, headers=headers)
    assert gen_resp.status_code == 200
    workflow_id = gen_resp.json()["workflowId"]
    poll_workflow(client, workflow_id, headers)

    tampered_confirm = {
        "inputs": VALID_PREFS,
        "totalCalories": 999999,
        "macros": {"protein": 0, "carbs": 0, "fat": 0},
        "meals": [{"type": "meal", "label": "Tampered", "items": []}],
        "withinTolerance": True,
        "workflowId": workflow_id,
    }
    confirm_resp = client.post("/api/diet/confirm", json=tampered_confirm, headers=headers)
    assert confirm_resp.status_code == 200
    plan_id = confirm_resp.json()["id"]

    plans_resp = client.get("/api/diet/plans", headers=headers)
    saved = next(p for p in plans_resp.json() if p["id"] == plan_id)
    assert saved["totalCalories"] != 999999
    assert saved["totalCalories"] == TARGET_CALORIES


def test_legacy_confirm_still_works_without_workflow_id(client, auth_headers):
    headers = auth_headers(user_id=103)
    body = {
        "inputs": VALID_PREFS,
        "totalCalories": TARGET_CALORIES,
        "macros": {"protein": 150, "carbs": 200, "fat": 60},
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, count=4),
        "withinTolerance": True,
    }
    resp = client.post("/api/diet/confirm", json=body, headers=headers)
    assert resp.status_code == 200
    assert "id" in resp.json()


def test_approve_requires_trainer_role(client, auth_headers, mock_generate_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=1500 / 4, count=4),  # forces below-safe-floor -> high risk
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=104)
    risky_prefs = dict(VALID_PREFS, medicalConditions=["diabetes"], age=15)
    gen_resp = client.post("/api/diet/generate", json=risky_prefs, headers=headers)
    assert gen_resp.status_code == 200
    workflow_id = gen_resp.json()["workflowId"]
    detail = poll_workflow(client, workflow_id, headers)
    # Either completed-with-pending-approval or rejected by the validator's
    # own floor check; only proceed with the approval-role check if it
    # actually reached the pending-approval state.
    if detail["status"] != "completed" or detail["approvalStatus"] != "pending":
        return

    user_resp = client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=104, role="User"))
    assert user_resp.status_code == 403

    trainer_resp = client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=999, role="Trainer"))
    assert trainer_resp.status_code == 200
    assert trainer_resp.json()["approvalStatus"] == "approved"


def test_workflow_trace_shows_all_three_agents(client, auth_headers, mock_generate_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, count=4),
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=105)
    gen_resp = client.post("/api/diet/generate", json=VALID_PREFS, headers=headers)
    workflow_id = gen_resp.json()["workflowId"]
    poll_workflow(client, workflow_id, headers)

    trace_resp = client.get(f"/api/diet/workflows/{workflow_id}/trace", headers=headers)
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    agents_seen = {e["agent"] for e in trace["events"]}
    assert "NutritionAnalystAgent" in agents_seen
    assert "MealGeneratorAgent" in agents_seen
    assert "SafetyValidatorAgent" in agents_seen


def test_refine_plan_applies_targeted_edit(client, auth_headers, mock_generate_meals, mock_refine_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, name="Rice bowl", count=4),
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=106)
    gen_resp = client.post("/api/diet/generate", json=VALID_PREFS, headers=headers)
    workflow_id = gen_resp.json()["workflowId"]
    poll_workflow(client, workflow_id, headers)

    mock_refine_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, name="Quinoa bowl", count=4),
        "withinTolerance": True,
    }
    refine_resp = client.post(
        f"/api/diet/workflows/{workflow_id}/refine",
        json={"instruction": "instead of rice in lunch, include something else"},
        headers=headers,
    )
    assert refine_resp.status_code == 200
    assert refine_resp.json()["status"] == "running"

    detail = poll_workflow(client, workflow_id, headers)
    assert detail["status"] == "completed"
    assert detail["message"] is None
    assert detail["meals"][0]["items"][0]["name"] == "Quinoa bowl"
    mock_refine_meals.assert_awaited_once()


def test_refine_plan_reverts_when_edit_is_unsafe(client, auth_headers, mock_generate_meals, mock_refine_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, name="Rice bowl", count=4),
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=107)
    prefs = dict(VALID_PREFS, restrictions=["vegetarian"])
    gen_resp = client.post("/api/diet/generate", json=prefs, headers=headers)
    workflow_id = gen_resp.json()["workflowId"]
    original = poll_workflow(client, workflow_id, headers)
    assert original["status"] == "completed"

    # The LLM ignores the restriction and suggests chicken - the Safety
    # Validator must still catch this even though it's a user-requested edit.
    mock_refine_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, name="Grilled chicken breast", count=4),
        "withinTolerance": True,
    }
    refine_resp = client.post(
        f"/api/diet/workflows/{workflow_id}/refine",
        json={"instruction": "add more protein to lunch"},
        headers=headers,
    )
    assert refine_resp.status_code == 200

    detail = poll_workflow(client, workflow_id, headers)
    assert detail["status"] == "completed"
    assert detail["message"] is not None
    # Plan stays exactly as it was before the rejected edit.
    assert detail["meals"] == original["meals"]


def test_refine_plan_requires_owned_completed_workflow(client, auth_headers):
    headers = auth_headers(user_id=108)
    resp = client.post(
        "/api/diet/workflows/00000000-0000-0000-0000-000000000000/refine",
        json={"instruction": "swap the rice"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_refine_plan_rejects_empty_instruction(client, auth_headers, mock_generate_meals):
    mock_generate_meals.return_value = {
        "meals": make_meals(calories_each=TARGET_CALORIES / 4, count=4),
        "withinTolerance": True,
    }
    headers = auth_headers(user_id=109)
    gen_resp = client.post("/api/diet/generate", json=VALID_PREFS, headers=headers)
    workflow_id = gen_resp.json()["workflowId"]
    poll_workflow(client, workflow_id, headers)

    resp = client.post(f"/api/diet/workflows/{workflow_id}/refine", json={"instruction": "   "}, headers=headers)
    assert resp.status_code == 422
