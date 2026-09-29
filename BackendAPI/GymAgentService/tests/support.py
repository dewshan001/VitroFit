"""Fakes and golden data shared by the tests."""

import asyncio

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool

from contracts import GymFacts, PlannerInput, Recommendations
from tools import ScrapeInput, SearchGymInput

WEBSITE = "https://fitzone.lk"

SITE_TEXT = (
    "FitZone Colombo. We have treadmills, squat racks and dumbbells. "
    "Classes: Yoga, Spin. Call us on +94 11 234 5678 or email info@fitzone.lk. "
    "Open 6am-10pm daily."
)


def gym_request(**overrides) -> PlannerInput:
    data = dict(place_id="place-1", name="FitZone", address="Colombo", website=WEBSITE)
    data.update(overrides)
    return PlannerInput(**data)


def fake_scrape_tool(text: str = SITE_TEXT) -> StructuredTool:
    async def scrape(url: str) -> str:
        return text

    return StructuredTool.from_function(
        coroutine=scrape, name="scrape_gym_website", description="fake", args_schema=ScrapeInput
    )


def fake_search_tool() -> StructuredTool:
    async def search(query: str) -> str:
        return "Web search unavailable: test"

    return StructuredTool.from_function(
        coroutine=search, name="search_gym_info", description="fake", args_schema=SearchGymInput
    )


def golden_facts(**overrides) -> GymFacts:
    data = dict(
        equipment=["treadmill", "squat rack", "dumbbell"],
        classes=["Yoga", "Spin"],
        phone="+94 11 234 5678",
        email="info@fitzone.lk",
        opening_hours="6am-10pm daily",
        evidence=[
            {"field": "equipment", "source_url": WEBSITE, "snippet": "We have treadmills, squat racks and dumbbells."},
            {"field": "classes", "source_url": WEBSITE, "snippet": "Classes: Yoga, Spin."},
            {"field": "phone", "source_url": WEBSITE, "snippet": "Call us on +94 11 234 5678"},
            {"field": "email", "source_url": WEBSITE, "snippet": "email info@fitzone.lk"},
            {"field": "opening_hours", "source_url": WEBSITE, "snippet": "Open 6am-10pm daily."},
        ],
        confidence=0.85,
    )
    data.update(overrides)
    return GymFacts.model_validate(data)


def workout(name, category="Strength", minutes=40, difficulty="Intermediate", used=("dumbbell",)):
    return {
        "name": name,
        "category": category,
        "duration_minutes": minutes,
        "difficulty": difficulty,
        "description": "A focused session using the listed gym equipment.",
        "equipment_used": list(used),
    }


def golden_recs(**overrides) -> Recommendations:
    data = dict(
        workouts=[
            workout("Upper Body Strength", used=("dumbbell", "squat rack")),
            workout("Treadmill Intervals", "HIIT", 30, "Advanced", ("treadmill",)),
            workout("Yoga Flow", "Flexibility", 45, "Beginner", ("Yoga",)),
            workout("Bodyweight Circuit", "Endurance", 25, "Beginner", ("bodyweight",)),
        ],
        notes="",
    )
    data.update(overrides)
    return Recommendations.model_validate(data)


class FakeModel:
    """Scripted stand-in for the chat model. Used as the `llm_factory` itself."""

    def __init__(self, tool_calls=None, facts=None, recs=None, fail=None, delay=0.0):
        self.tool_calls = tool_calls if tool_calls is not None else [
            {"name": "scrape_gym_website", "args": {"url": WEBSITE}, "id": "call-1", "type": "tool_call"}
        ]
        self.facts = facts if facts is not None else golden_facts()
        self.recs_queue = list(recs) if recs else [golden_recs()]
        self.fail = fail
        self.delay = delay
        self.bound_tool_names: list[str] = []
        self.prompts: list[list] = []

    def __call__(self, **_kwargs):
        return self

    def bind_tools(self, tools):
        self.bound_tool_names = [t.name for t in tools]
        return self

    async def _gate(self, messages):
        self.prompts.append(messages)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise self.fail

    async def ainvoke(self, messages):
        await self._gate(messages)
        if self.tool_calls and not any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(content="", tool_calls=self.tool_calls)
        return AIMessage(content="done")

    def with_structured_output(self, schema):
        outer = self

        class Structured:
            async def ainvoke(self, messages):
                await outer._gate(messages)
                if schema is GymFacts:
                    return outer.facts
                recs = outer.recs_queue[0] if len(outer.recs_queue) == 1 else outer.recs_queue.pop(0)
                return recs

        return Structured()

    def all_prompt_text(self) -> str:
        return "\n".join(str(getattr(m, "content", m)) for turn in self.prompts for m in turn)
