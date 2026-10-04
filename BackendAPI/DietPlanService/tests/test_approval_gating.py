# DietPlanService/tests/test_approval_gating.py
"""High-risk plans cannot be saved until a Trainer/Admin approves; low and medium
risk behave exactly as before; a decision is made once and only by an approver."""
from conftest import (
    VALID_PREFS, HIGH_RISK_PREFS, generate_and_wait, confirm_body, make_meals,
    expected_target_calories, new_user_id, poll_workflow,
)


def _high_risk_workflow(client, auth_headers, mock_generate_meals):
    user_id = new_user_id()
    headers = auth_headers(user_id=user_id)
    workflow_id, detail = generate_and_wait(client, headers, HIGH_RISK_PREFS, mock_generate_meals)
    assert detail["status"] == "completed"
    assert detail["riskLevel"] == "high"
    assert detail["approvalStatus"] == "pending"
    return user_id, headers, workflow_id


def test_low_risk_plan_is_saved_without_any_approval(client, auth_headers, mock_generate_meals):
    headers = auth_headers(user_id=new_user_id())
    workflow_id, detail = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    assert detail["approvalStatus"] == "auto_approved"
    resp = client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, workflow_id), headers=headers)
    assert resp.status_code == 200


def test_high_risk_plan_cannot_be_saved_until_approved(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)

    blocked = client.post("/api/diet/confirm", json=confirm_body(HIGH_RISK_PREFS, workflow_id), headers=headers)
    assert blocked.status_code == 409
    assert isinstance(blocked.json()["detail"], str)  # the web client shows `detail` as the error text
    assert "approval" in blocked.json()["detail"]

    approve = client.post(f"/api/diet/workflows/{workflow_id}/approve?note=looks%20fine", headers=auth_headers(user_id=1, role="Trainer"))
    assert approve.status_code == 200
    assert approve.json()["approvalStatus"] == "approved"

    saved = client.post("/api/diet/confirm", json=confirm_body(HIGH_RISK_PREFS, workflow_id), headers=headers)
    assert saved.status_code == 200


def test_approval_records_who_decided_and_when(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=77, role="Admin"))

    detail = client.get(f"/api/diet/workflows/{workflow_id}", headers=headers).json()
    assert detail["approvedBy"] == 77
    assert detail["approverRole"] == "Admin"
    assert detail["decidedAt"]
    trace = client.get(f"/api/diet/workflows/{workflow_id}/trace", headers=headers).json()
    assert any(e["agent"] == "approval" and e["tool"] == "approve" and e["approverRole"] == "Admin" for e in trace["events"])


def test_rejected_plan_can_never_be_saved(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    reject = client.post(f"/api/diet/workflows/{workflow_id}/reject?note=too%20aggressive", headers=auth_headers(user_id=2, role="Trainer"))
    assert reject.status_code == 200

    blocked = client.post("/api/diet/confirm", json=confirm_body(HIGH_RISK_PREFS, workflow_id), headers=headers)
    assert blocked.status_code == 409
    assert "declined" in blocked.json()["detail"] and "too aggressive" in blocked.json()["detail"]


def test_a_plan_is_decided_only_once(client, auth_headers, mock_generate_meals):
    _, _, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    trainer = auth_headers(user_id=3, role="Trainer")
    assert client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=trainer).status_code == 200
    again = client.post(f"/api/diet/workflows/{workflow_id}/reject?note=changed%20my%20mind", headers=trainer)
    assert again.status_code == 409
    assert client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=trainer).status_code == 409


def test_plain_users_cannot_decide(client, auth_headers, mock_generate_meals):
    user_id, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    assert client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=headers).status_code == 403
    assert client.post(f"/api/diet/workflows/{workflow_id}/reject?note=x", headers=headers).status_code == 403


def test_only_plans_waiting_for_review_can_be_decided(client, auth_headers, mock_generate_meals):
    headers = auth_headers(user_id=new_user_id())
    workflow_id, detail = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    assert detail["approvalStatus"] == "auto_approved"
    resp = client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=4, role="Trainer"))
    assert resp.status_code == 409


def test_pending_queue_lists_high_risk_plans_for_reviewers_only(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    assert client.get("/api/diet/approvals/pending", headers=headers).status_code == 403
    queue = client.get("/api/diet/approvals/pending", headers=auth_headers(user_id=5, role="Trainer")).json()
    assert workflow_id in [row["id"] for row in queue]


def test_legacy_confirm_without_workflow_id_is_refused_for_high_risk(client, auth_headers):
    headers = auth_headers(user_id=new_user_id())
    resp = client.post("/api/diet/confirm", json=confirm_body(HIGH_RISK_PREFS), headers=headers)
    assert resp.status_code == 409
    assert isinstance(resp.json()["detail"], str)


def test_legacy_confirm_cannot_dodge_risk_by_sending_fake_calories(client, auth_headers):
    # Risk is judged on targets recomputed server-side, not on the numbers the client claims.
    headers = auth_headers(user_id=new_user_id())
    body = confirm_body(dict(VALID_PREFS, gender="female", age=16, medicalConditions=["diabetes"], weightKg=30, heightCm=100, goal="weight loss", activityLevel="sedentary"),
                        calories=2500)
    resp = client.post("/api/diet/confirm", json=body, headers=headers)
    assert resp.status_code == 409


def test_legacy_confirm_still_rejects_unsafe_meals(client, auth_headers):
    headers = auth_headers(user_id=new_user_id())
    prefs = dict(VALID_PREFS, restrictions=["vegetarian"])
    body = confirm_body(prefs, meals=make_meals(calories_each=expected_target_calories(prefs) / 4, name="Grilled chicken breast", count=4))
    resp = client.post("/api/diet/confirm", json=body, headers=headers)
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


def test_update_plan_applies_the_same_gate_and_validation(client, auth_headers, mock_generate_meals):
    user_id = new_user_id()
    headers = auth_headers(user_id=user_id)
    workflow_id, _ = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    plan_id = client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, workflow_id), headers=headers).json()["id"]

    # An update used to store whatever meals the client sent. Unsafe meals are now refused...
    veg = dict(VALID_PREFS, restrictions=["vegetarian"])
    bad = confirm_body(veg, meals=make_meals(calories_each=expected_target_calories(veg) / 4, name="Beef curry", count=4))
    assert client.put(f"/api/diet/plans/{plan_id}", json=bad, headers=headers).status_code == 422

    # ...a high-risk regenerated plan waits for approval...
    risky_id, _ = generate_and_wait(client, headers, HIGH_RISK_PREFS, mock_generate_meals)
    pending = client.put(f"/api/diet/plans/{plan_id}", json=confirm_body(HIGH_RISK_PREFS, risky_id), headers=headers)
    assert pending.status_code == 409

    # ...and once approved the update goes through and saves the workflow's own plan.
    client.post(f"/api/diet/workflows/{risky_id}/approve", headers=auth_headers(user_id=6, role="Trainer"))
    ok = client.put(f"/api/diet/plans/{plan_id}", json=confirm_body(HIGH_RISK_PREFS, risky_id), headers=headers)
    assert ok.status_code == 200
    saved = next(p for p in client.get("/api/diet/plans", headers=headers).json() if p["id"] == plan_id)
    assert saved["totalCalories"] == expected_target_calories(HIGH_RISK_PREFS)


def test_confirm_with_someone_elses_workflow_is_404(client, auth_headers, mock_generate_meals):
    owner = auth_headers(user_id=new_user_id())
    workflow_id, _ = generate_and_wait(client, owner, VALID_PREFS, mock_generate_meals)
    other = auth_headers(user_id=new_user_id())
    assert client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, workflow_id), headers=other).status_code == 404


def test_confirm_with_malformed_workflow_id_is_404_not_500(client, auth_headers):
    headers = auth_headers(user_id=new_user_id())
    resp = client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, "not-a-uuid"), headers=headers)
    assert resp.status_code == 404


def test_editing_an_approved_high_risk_plan_needs_a_new_review(client, auth_headers, mock_generate_meals, mock_refine_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=8, role="Trainer"))

    mock_refine_meals.return_value = {
        "meals": make_meals(calories_each=expected_target_calories(HIGH_RISK_PREFS) / 4, name="Quinoa bowl", count=4),
        "withinTolerance": True,
    }
    resp = client.post(f"/api/diet/workflows/{workflow_id}/refine", json={"instruction": "swap the chicken for fish"}, headers=headers)
    assert resp.status_code == 200
    detail = poll_workflow(client, workflow_id, auth_headers(user_id=8, role="Trainer"))  # the owner's own view hides pending content
    assert detail["meals"][0]["items"][0]["name"] == "Quinoa bowl"
    assert detail["approvalStatus"] == "pending"
    assert detail["approvedBy"] is None
    assert client.post("/api/diet/confirm", json=confirm_body(HIGH_RISK_PREFS, workflow_id), headers=headers).status_code == 409


def test_a_second_decision_explains_that_the_plan_is_no_longer_waiting(client, auth_headers, mock_generate_meals):
    _, _, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    trainer = auth_headers(user_id=3, role="Trainer")
    client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=trainer)
    again = client.post(f"/api/diet/workflows/{workflow_id}/reject?note=x", headers=trainer)
    assert again.status_code == 409 and "isn't waiting for review" in again.json()["detail"]


def test_two_reviewers_racing_cannot_both_decide(client, auth_headers, mock_generate_meals):
    """The second reviewer's session still sees the plan as pending (stale read); the conditional
    UPDATE is what stops them from overwriting the first reviewer's decision."""
    import uuid
    import pytest
    from fastapi import HTTPException
    from src.api import routes
    from src.models.db_models import DietWorkflow
    from src.utils.db import SessionLocal

    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    slow_reviewer = SessionLocal()
    try:
        stale = slow_reviewer.get(DietWorkflow, uuid.UUID(workflow_id))   # keep the reference so the session keeps its stale copy
        assert stale.approval_status == "pending"                          # read, then...
        client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=11, role="Trainer"))  # ...someone else decides
        with pytest.raises(HTTPException) as err:
            routes._decide(workflow_id, "reject", "late", {"sub": "12", "role": "Admin"}, slow_reviewer)
        assert err.value.status_code == 409 and "Another reviewer" in err.value.detail
    finally:
        slow_reviewer.close()
    final = client.get(f"/api/diet/workflows/{workflow_id}", headers=headers).json()
    assert final["approvalStatus"] == "approved" and final["approvedBy"] == 11


def test_legacy_confirm_saves_server_calculated_targets_not_the_clients(client, auth_headers):
    headers = auth_headers(user_id=new_user_id())
    resp = client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, calories=999), headers=headers)
    assert resp.status_code == 200
    saved = client.get("/api/diet/plans", headers=headers).json()[0]
    assert saved["totalCalories"] == expected_target_calories(VALID_PREFS)


# --- pending plans: saved for the customer at generation, content hidden until approved ---

def test_high_risk_plan_is_listed_as_pending_without_content(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    plans = client.get("/api/diet/plans", headers=headers).json()
    assert len(plans) == 1
    assert plans[0]["approvalStatus"] == "pending"
    assert set(plans[0]) == {"id", "createdAt", "approvalStatus"}  # no meals, calories or inputs


def test_owner_sees_no_plan_content_while_pending_but_the_reviewer_does(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    own = client.get(f"/api/diet/workflows/{workflow_id}", headers=headers).json()
    assert own["meals"] is None and own["targets"] is None and own["finalOutcome"] is None
    reviewer = client.get(f"/api/diet/workflows/{workflow_id}", headers=auth_headers(user_id=1, role="Admin")).json()
    assert reviewer["meals"] and reviewer["targets"]["totalCalories"] == expected_target_calories(HIGH_RISK_PREFS)
    assert reviewer["inputs"]["medicalConditions"] == ["diabetes"]
    assert reviewer["riskFlags"]


def test_pending_queue_lists_flags_and_calories(client, auth_headers, mock_generate_meals):
    _, _, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    queue = client.get("/api/diet/approvals/pending", headers=auth_headers(user_id=1, role="Admin")).json()
    row = next(r for r in queue if r["id"] == workflow_id)
    assert row["totalCalories"] == expected_target_calories(HIGH_RISK_PREFS)
    assert row["riskFlags"]


def test_approval_reveals_the_plan_and_saving_does_not_duplicate_it(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    client.post(f"/api/diet/workflows/{workflow_id}/approve", headers=auth_headers(user_id=1, role="Admin"))
    plans = client.get("/api/diet/plans", headers=headers).json()
    assert len(plans) == 1 and plans[0]["approvalStatus"] == "approved"
    assert plans[0]["totalCalories"] == expected_target_calories(HIGH_RISK_PREFS) and plans[0]["meals"]
    saved = client.post("/api/diet/confirm", json=confirm_body(HIGH_RISK_PREFS, workflow_id), headers=headers)
    assert saved.status_code == 200 and saved.json()["id"] == plans[0]["id"]
    assert len(client.get("/api/diet/plans", headers=headers).json()) == 1


def test_rejection_removes_the_pending_plan_from_the_list(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    resp = client.post(f"/api/diet/workflows/{workflow_id}/reject?note=unsafe", headers=auth_headers(user_id=1, role="Admin"))
    assert resp.status_code == 200
    assert client.get("/api/diet/plans", headers=headers).json() == []
    own = client.get(f"/api/diet/workflows/{workflow_id}", headers=headers).json()
    assert own["approvalStatus"] == "rejected" and own["approvalNote"] == "unsafe"


def test_a_pending_plan_cannot_be_edited(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    plan_id = client.get("/api/diet/plans", headers=headers).json()[0]["id"]
    resp = client.put(f"/api/diet/plans/{plan_id}", json=confirm_body(HIGH_RISK_PREFS, workflow_id), headers=headers)
    assert resp.status_code == 409


def test_deleting_a_pending_plan_removes_it_from_the_review_queue(client, auth_headers, mock_generate_meals):
    _, headers, workflow_id = _high_risk_workflow(client, auth_headers, mock_generate_meals)
    plan_id = client.get("/api/diet/plans", headers=headers).json()[0]["id"]
    assert client.delete(f"/api/diet/plans/{plan_id}", headers=headers).status_code == 204
    queue = client.get("/api/diet/approvals/pending", headers=auth_headers(user_id=1, role="Admin")).json()
    assert workflow_id not in [r["id"] for r in queue]


def test_low_risk_plans_are_never_listed_as_pending(client, auth_headers, mock_generate_meals):
    headers = auth_headers(user_id=new_user_id())
    workflow_id, _ = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    assert client.get("/api/diet/plans", headers=headers).json() == []
    client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, workflow_id), headers=headers)
    assert client.get("/api/diet/plans", headers=headers).json()[0]["approvalStatus"] == "approved"
