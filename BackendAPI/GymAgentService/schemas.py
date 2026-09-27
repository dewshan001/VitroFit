"""Pydantic schemas for structured LLM output — guaranteed valid, no regex needed."""

from pydantic import BaseModel, Field


class GymEnrichmentResult(BaseModel):
    """Structured output the LLM must return when extracting gym data."""

    equipment: list[str] = Field(
        default_factory=list,
        description=(
            "List of gym equipment "
            "(e.g. treadmill, squat rack, cable machine, free weights, pool)"
        ),
    )
    classes: list[str] = Field(
        default_factory=list,
        description=(
            "List of classes or programs offered "
            "(e.g. yoga, CrossFit, spin, personal training)"
        ),
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "How confident you are in the accuracy of this data "
            "(0.0 = pure guess, 1.0 = clearly stated on website)"
        ),
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of where this information was found or why it was inferred",
    )
    phone: str | None = Field(
        default=None,
        description=(
            "Gym's phone number, ONLY if explicitly present in the scraped website text "
            "or search results. Leave null if not found. Never guess or invent a phone number."
        ),
    )
    email: str | None = Field(
        default=None,
        description=(
            "Gym's contact email, ONLY if explicitly present in the scraped website text "
            "or search results. Leave null if not found. Never guess or invent an email."
        ),
    )
    opening_hours: str | None = Field(
        default=None,
        description=(
            "Gym's opening hours, ONLY if explicitly present in the scraped website text "
            "or search results. Leave null if not found. Never guess or invent hours."
        ),
    )


class WorkoutSuggestion(BaseModel):
    """A single suggested workout tailored to a gym's available equipment/classes."""

    name: str = Field(description="Short, specific workout name (e.g. 'Upper Body Strength Circuit')")
    category: str = Field(
        description="Workout category, e.g. Strength, Cardio, HIIT, Flexibility, Endurance"
    )
    duration_minutes: int = Field(
        ge=5, le=180, description="Estimated workout duration in minutes"
    )
    difficulty: str = Field(description="Beginner, Intermediate, or Advanced")
    description: str = Field(
        description="1-2 short sentences describing what the workout involves and how to do it"
    )
    equipment_used: list[str] = Field(
        default_factory=list,
        description=(
            "At most 2-3 of the most relevant equipment/class items from this gym's list "
            "that this workout uses — do not repeat the gym's full equipment list here."
        ),
    )


class WorkoutSuggestions(BaseModel):
    """Structured output for a gym's AI-suggested workouts."""

    workouts: list[WorkoutSuggestion] = Field(
        default_factory=list,
        description="Exactly 4 suggested workouts a visitor could do at this gym",
    )
    notes: str = Field(
        default="",
        description=(
            "Short caveat for the user, e.g. noting suggestions are generic because "
            "little equipment/class info is known for this gym. Empty string if not needed."
        ),
    )


class GymSearchResult(BaseModel):
    """Structured output for web search results about a gym."""

    found_info: bool = Field(description="Whether useful information was found")
    equipment_mentions: list[str] = Field(default_factory=list)
    class_mentions: list[str] = Field(default_factory=list)
    source_summary: str = Field(
        default="", description="Brief summary of what was found"
    )

