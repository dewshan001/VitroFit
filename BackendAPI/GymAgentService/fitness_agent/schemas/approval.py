# BackendAPI/GymAgentService/fitness_agent/schemas/approval.py
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_REVISION = "REQUEST_REVISION"


class ApprovalRequest(BaseModel):
    workflow_id: str
    approver_id: int
    decision: ApprovalDecision
    reason: Optional[str] = None


class ApprovalResult(BaseModel):
    workflow_id: str
    status: str
    decision: ApprovalDecision
    approver_id: int
    timestamp: str
