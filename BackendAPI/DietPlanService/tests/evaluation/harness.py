"""Runs one golden case through the real API, coordinator, validator and database, and checks the outcome.

Only the outside world is scripted: the model's replies (the meal-generation tool is replaced by a
queue of replies) and the clock's time budget. Everything the assignment wants evidenced (planning,
delegation, tool selection, structured outputs, deterministic validation, business rules, approval
enforcement, injection resistance, failure recovery, safe failure) is checked with plain assertions
on stored data. No LLM-as-judge.
"""
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import select

from conftest import (
    VALID_PREFS, confirm_body, expected_target_calories, make_meals, new_user_id, poll_workflow,
)
from src.models.db_models import DietWorkflowStep
from src.utils.db import SessionLocal

CRITERIA = (
    "planning",
    "delegation",
    "tool_selection",
    "structured_outputs",
    "deterministic_validation",
    "business_rules",
    "approval_enforcement",
    "prompt_injection_resistance",
    "failure_recovery",
    "safe_failure",
)


@dataclass
class Expect:
    criterion: str
    name: str
    key: str                 # which observation of the case to look at
    expected: Any
    op: str = "eq"           # eq | contains | gte | subset


@dataclass
class Case:
    id: str
    title: str
    run: Callable[["Harness"], dict]
    expects: list[Expect]


@dataclass
class Check:
    case_id: str
    criterion: str
    name: str
    expected: Any
    observed: Any
    passed: bool


class Harness:
    """The scripted world a case runs in."""

    def __init__(self, client, auth_headers, mock_generate, mock_refine):
        self.client, self._auth, self.gen, self.refine_mock = client, auth_headers, mock_generate, mock_refine

    # -- people ----------------------------------------------------------------------
    def headers(self, role="User", user_id=None):
        return self._auth(user_id=user_id or new_user_id(), role=role)

    # -- actions ---------------------------------------------------------------------
    @staticmethod
    def on_target(prefs=VALID_PREFS, name="Grilled chicken bowl", scale=1.0):
        return {"meals": make_meals(expected_target_calories(prefs) * scale / 4, name=name, count=4), "withinTolerance": True}

    def generate(self, headers, prefs, replies=None):
        self.gen.side_effect = None
        self.gen.reset_mock()
        replies = replies if replies is not None else [self.on_target(prefs)]
        self.gen.side_effect = replies if len(replies) > 1 else None
        if len(replies) == 1:
            self.gen.return_value = replies[0]
        resp = self.client.post("/api/diet/generate", json=prefs, headers=headers)
        if resp.status_code != 200:
            return None, resp
        workflow_id = resp.json()["workflowId"]
        return workflow_id, poll_workflow(self.client, workflow_id, headers)

    def refine(self, headers, workflow_id, instruction, reply=None):
        self.refine_mock.reset_mock()
        if reply is not None:
            self.refine_mock.return_value = reply
        resp = self.client.post(f"/api/diet/workflows/{workflow_id}/refine", json={"instruction": instruction}, headers=headers)
        if resp.status_code != 200:
            return resp
        return poll_workflow(self.client, workflow_id, headers)

    def decide(self, workflow_id, decision, role="Trainer", note="eval"):
        suffix = f"?note={note}" if decision == "reject" else ""
        return self.client.post(f"/api/diet/workflows/{workflow_id}/{decision}{suffix}", headers=self.headers(role=role))

    def confirm(self, headers, prefs, workflow_id=None, **kwargs):
        return self.client.post("/api/diet/confirm", json=confirm_body(prefs, workflow_id, **kwargs), headers=headers)

    # -- observations ----------------------------------------------------------------
    def trace(self, headers, workflow_id):
        return self.client.get(f"/api/diet/workflows/{workflow_id}/trace", headers=headers).json()

    def agents_in(self, headers, workflow_id):
        return [e["agent"] for e in self.trace(headers, workflow_id)["events"]]

    def step_rows(self, workflow_id):
        session = SessionLocal()
        try:
            return session.execute(
                select(DietWorkflowStep).where(DietWorkflowStep.workflow_id == uuid.UUID(workflow_id)).order_by(DietWorkflowStep.seq)
            ).scalars().all()
        finally:
            session.close()

    def saved_count(self, headers):
        # Plans awaiting review are listed for the customer without content, so they are not "saved" yet.
        plans = self.client.get("/api/diet/plans", headers=headers).json()
        return len([p for p in plans if p.get("approvalStatus") != "pending"])

    def db(self):
        return SessionLocal()


def _observed_ok(expect: Expect, observed: Any) -> bool:
    if expect.op == "eq":
        return observed == expect.expected
    if expect.op == "contains":
        return expect.expected in observed
    if expect.op == "gte":
        return observed >= expect.expected
    if expect.op == "subset":
        return set(expect.expected) <= set(observed)
    raise ValueError(expect.op)


def evaluate(case: Case, facts: dict) -> list[Check]:
    checks = []
    for e in case.expects:
        observed = facts.get(e.key, "<missing>")
        try:
            passed = e.key in facts and _observed_ok(e, observed)
        except Exception:
            passed = False
        checks.append(Check(case.id, e.criterion, e.name, e.expected, observed, passed))
    return checks

