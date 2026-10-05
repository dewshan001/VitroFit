"""Planner agent: turns a domain objective into a structured, delegated plan.

Deterministic on purpose (no LLM, no tools): routing a data-collection job is a
rules decision and must be reproducible. Its output narrows what the analysis
agent may do (least privilege), e.g. no scraping when there is no website.
"""

from src.models.contracts import Plan, PlannerInput, PlanStep


def run(inp: PlannerInput) -> Plan:
    has_site = bool(inp.website and inp.website.strip())
    route = "scrape" if has_site else "search"
    analysis_tools = (
        ["scrape_gym_website", "search_gym_info", "lookup_similar_gyms"]
        if has_site
        else ["search_gym_info", "lookup_similar_gyms"]
    )
    steps = [
        PlanStep(
            id="s1",
            agent="gym_analysis",
            action=f"Collect equipment, classes and contact details via '{route}' route",
        ),
        PlanStep(
            id="s2",
            agent="workout_recommendation",
            action="Recommend four workouts using only the collected equipment/classes",
            depends_on=["s1"],
        ),
        PlanStep(
            id="s3",
            agent="validator",
            action="Apply deterministic evidence, business-rule and safety checks",
            depends_on=["s1", "s2"],
        ),
    ]
    rationale = (
        "Gym has a website: scrape it first, fall back to search and similar-gym lookup."
        if has_site
        else "No website available: use web search and similar-gym lookup only; scraping is not permitted."
    )
    return Plan(route=route, analysis_tools=analysis_tools, steps=steps, rationale=rationale)
