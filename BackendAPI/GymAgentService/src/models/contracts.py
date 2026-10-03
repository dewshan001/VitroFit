"""Input/output contracts for the four gym-workflow agents.

Every model forbids unknown fields, so an agent cannot receive or emit data outside
its contract. Each agent reads only its own *Input model and returns only its own
output model; the graph state carries them between agents.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.utils.injection_guard import normalise_field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Shared vocabulary ───────────────────────────────────────────────────

# Roles allowed to approve, reject or revise. Enforced by ASP.NET, the runner, the graph's
# approval gate, and (last line of defence) store.publish.
APPROVER_ROLES = frozenset({"Gym_Owner", "Admin"})

AgentName = Literal["planner", "gym_analysis", "workout_recommendation", "validator"]
Route = Literal["scrape", "search", "rag"]
Difficulty = Literal["Beginner", "Intermediate", "Advanced"]
Decision = Literal["approve", "reject", "revise"]
EvidenceField = Literal["equipment", "classes", "phone", "email", "opening_hours"]


# ── 1. Planner ──────────────────────────────────────────────────────────


class PlannerInput(Contract):
    place_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=500)
    known_phone: str | None = Field(default=None, max_length=50)
    known_email: str | None = Field(default=None, max_length=255)
    known_hours: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None
    objective: str = Field(
        default="Collect verified equipment, classes and contact details for this gym "
        "and recommend four workouts that use them.",
        max_length=500,
    )

    @field_validator(
        "place_id", "name", "address", "website", "known_phone", "known_email", "known_hours", "objective",
        mode="before",
    )
    @classmethod
    def _normalise(cls, value):
        # OpenStreetMap text is editable by anyone: strip NUL/invisible/control characters on the way in.
        return normalise_field(value) if isinstance(value, str) else value


class PlanStep(Contract):
    id: str
    agent: AgentName
    action: str
    depends_on: list[str] = Field(default_factory=list)


class Plan(Contract):
    route: Route
    # Least privilege: tools the gym_analysis agent may use for this run.
    analysis_tools: list[str]
    steps: list[PlanStep]
    rationale: str


# ── 2. Gym analysis ─────────────────────────────────────────────────────


class Evidence(Contract):
    field: EvidenceField
    source_url: str | None = Field(default=None, max_length=500)
    snippet: str = Field(min_length=1, max_length=400)

    @field_validator("snippet", mode="before")
    @classmethod
    def _clip_snippet(cls, value):
        # Models often overshoot the "max 300 chars" instruction. A prefix of a verbatim quote is
        # still verbatim, so clip it rather than fail the whole analysis over length.
        return value.strip()[:300] if isinstance(value, str) else value


class AnalysisInput(Contract):
    gym: PlannerInput
    plan: Plan
    feedback: list[str] = Field(default_factory=list)


class GymFacts(Contract):
    equipment: list[str] = Field(default_factory=list, max_length=60)
    classes: list[str] = Field(default_factory=list, max_length=60)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    evidence: list[Evidence] = Field(default_factory=list, max_length=80)
    confidence: float = Field(ge=0.0, le=1.0)


# ── 3. Workout recommendation ───────────────────────────────────────────


class Workout(Contract):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    duration_minutes: int
    difficulty: Difficulty
    description: str = Field(min_length=1, max_length=400)
    equipment_used: list[str] = Field(default_factory=list, max_length=6)


class RecommendInput(Contract):
    name: str
    facts: GymFacts
    feedback: list[str] = Field(default_factory=list)


class Recommendations(Contract):
    workouts: list[Workout]
    notes: str = Field(default="", max_length=500)


# ── 4. Validator / safety ───────────────────────────────────────────────


class ValidatorInput(Contract):
    gym: PlannerInput
    plan: Plan
    facts: GymFacts
    recommendations: Recommendations
    # Text actually returned by tools (already sanitised); used to prove evidence.
    corpus: list[str] = Field(default_factory=list)
    # Pages actually fetched (scraped URL, search-result sources); a cited URL must be one of these.
    retrieved_urls: list[str] = Field(default_factory=list)


class Violation(Contract):
    code: str
    field: str | None = None
    message: str
    target: Literal["gym_analysis", "workout_recommendation"]
    # revise: the agent can fix it and is sent back. reject: it cannot be fixed by retrying.
    severity: Literal["revise", "reject"] = "revise"


class Verdict(Contract):
    verdict: Literal["pass", "revise", "reject"]
    violations: list[Violation] = Field(default_factory=list)


# ── Human approval ──────────────────────────────────────────────────────


class ApprovalDecision(Contract):
    decision: Decision
    reason: str = Field(default="", max_length=500)
    actor_id: str = Field(min_length=1, max_length=100)
    actor_role: str = Field(min_length=1, max_length=30)

    @field_validator("reason", "actor_id", "actor_role", mode="before")
    @classmethod
    def _normalise(cls, value):
        return normalise_field(value) if isinstance(value, str) else value
