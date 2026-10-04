# DietPlanService/src/tools/tool_registry.py
"""Per-agent tool allow-lists - the single place that says which agent may call
which tool. workflow.call_tool() enforces it (and, when the planner narrowed the
run, the plan's own list as well). An agent can never invoke a tool outside its
own list.
"""

# agent name -> tool names that agent may call. Anything absent means "no tools".
TOOL_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "NutritionAnalystAgent": ("calculate_targets", "assess_risk", "lookup_budget"),
    "MealGeneratorAgent": ("generate_meals", "refine_meals"),
    "SafetyValidatorAgent": ("validate_plan",),
}


def tools_for(agent_name: str) -> list[str]:
    return list(TOOL_PERMISSIONS.get(agent_name, ()))


def is_allowed(agent_name: str, tool: str, plan_allowed: list[str] | None = None) -> bool:
    """True when the agent's role allows the tool AND (if given) the plan for this run allows it."""
    if tool not in TOOL_PERMISSIONS.get(agent_name, ()):
        return False
    return plan_allowed is None or tool in plan_allowed
