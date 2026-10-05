"""Extraction prompts and JSON output shapes for the gym agents (moved verbatim)."""

GYM_ANALYSIS_EXTRACTION_PROMPT = (
    "From the conversation above, produce the final structured facts.\n"
    "- evidence: for the equipment list, the classes list, and each contact field you fill, add an "
    "entry {field, source_url, snippet}. The snippet must be copied VERBATIM (max 300 chars) from "
    "the retrieved text. source_url is required: it must be the exact URL of a page a tool retrieved "
    "(the URL you scraped, or the URL on a 'Source:' line of the search results) and must be on the "
    "allowed-sources list given in the task. Facts you cannot cite that way must be left out.\n"
    "- confidence: 0.8-1.0 if from the gym's own website, 0.5-0.7 if from web search, "
    "0.2-0.4 if inferred from similar gyms or the name.\n"
    "- Leave phone/email/opening_hours null unless explicitly present in the retrieved text."
)

GYM_ANALYSIS_JSON_SHAPE = (
    '\nRespond with ONLY a JSON object: {"equipment": [], "classes": [], "phone": null, '
    '"email": null, "opening_hours": null, "evidence": [{"field": "equipment", '
    '"source_url": null, "snippet": "..."}], "confidence": 0.5}'
)

WORKOUT_RECOMMENDATION_JSON_SHAPE = (
    "\n\nRespond with ONLY a JSON object of this exact shape, no other text:\n"
    '{"workouts": [{"name": "...", "category": "...", "duration_minutes": 30, '
    '"difficulty": "Beginner|Intermediate|Advanced", "description": "...", '
    '"equipment_used": ["..."]}], "notes": "..."}'
)
