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


class GymSearchResult(BaseModel):
    """Structured output for web search results about a gym."""

    found_info: bool = Field(description="Whether useful information was found")
    equipment_mentions: list[str] = Field(default_factory=list)
    class_mentions: list[str] = Field(default_factory=list)
    source_summary: str = Field(
        default="", description="Brief summary of what was found"
    )

