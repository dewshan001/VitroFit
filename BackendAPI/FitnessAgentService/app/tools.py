"""Least-privilege tools: read only the server-supplied, user-scoped snapshot.

No model receives SQL, filesystem, network URLs, or approval tools.
"""
from .schemas import Exercise, GenerateRequest


def exercise_search(request: GenerateRequest) -> list[Exercise]:
    confirmed = set(request.profile.equipment) | {"bodyweight"}
    return [e for e in request.catalog if e.beginnerAllowed and e.equipment in confirmed]


def progress_history(request: GenerateRequest) -> dict:
    return {
        "previousPlan": request.previousPlan.model_dump() if request.previousPlan else None,
        "progress": [p.model_dump() for p in request.progress],
    }


TOOL_PERMISSIONS = {
    "coordinator": (),
    "screening": (),
    "progress_analyst": ("progress_history",),
    "planner": ("exercise_search",),
    "validator": (),
}


def call_tool(role: str, name: str, request: GenerateRequest):
    if name not in TOOL_PERMISSIONS.get(role, ()):
        raise PermissionError("Tool is not allowed for this role")
    return {"exercise_search": exercise_search, "progress_history": progress_history}[name](request)
