import json
import httpx
from pydantic import ValidationError
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from .schemas import GenerateRequest, Timetable

# One shared env file for the whole backend (BackendAPI/.env), independent of the working directory.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class PlannerError(RuntimeError):
    pass

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")
    openrouter_api_key: str = ""
    openrouter_model: str = ""

def parse_chat_completion(payload: dict) -> Timetable:
    try:
        choice = payload["choices"][0]
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise PlannerError("MODEL_OUTPUT_EMPTY")
        # Strip markdown fences if present
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            stripped = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return Timetable.model_validate_json(stripped)
    except PlannerError:
        raise
    except ValidationError as e:
        print(f"ValidationError: {e}")
        print(f"Content: {content}")
        raise PlannerError("MODEL_OUTPUT_INVALID_PLAN_SCHEMA") from None
    except (KeyError, IndexError, TypeError, ValueError):
        raise PlannerError("MODEL_OUTPUT_INVALID_RESPONSE") from None

async def _call_openrouter(messages: list, format_json: bool = False):
    settings = Settings()
    if not settings.openrouter_api_key or not settings.openrouter_model:
        raise RuntimeError("LLM_NOT_CONFIGURED")
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            payload = {
                "model": settings.openrouter_model,
                "temperature": 0,
                "max_tokens": 4000,
                "messages": messages
            }
            if format_json:
                payload["response_format"] = {"type": "json_object"}
                
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        raise PlannerError(f"API_ERROR: {exc}")

async def propose_timetable(request: GenerateRequest, errors: list[str]) -> Timetable:
    context = {
        "plan": request.plan,
        "profile": request.profile,
        "preferences": request.preferences,
        "errors": errors,
        "outputSchema": Timetable.model_json_schema(),
    }
    messages = [
        {"role": "system", "content": "You are a time management scheduling assistant. Output ONLY a raw JSON object matching the outputSchema. No markdown, no code fences, no explanation - just the JSON.\n\nCRITICAL STRUCTURE RULES:\n1. The output must have exactly ONE 'slots' array containing ALL slots for ALL 7 days combined in a single flat list. Do NOT output one 'slots' per day.\n2. Each slot must have: day (1-7), startTime (HH:MM), endTime (HH:MM), focus, durationMinutes, description.\n3. The 'description' field MUST contain a comma-separated list of 3-5 specific exercises/activities for EVERY slot.\n\nSCHEDULE REQUIREMENTS:\n- For each workout day in the plan, create a dedicated slot with the workout's focus.\n- For ALL 7 days, add 3-4 extra lifestyle slots such as Morning Cardio, Meal Prep, Active Recovery, Mobility & Stretching, Yoga.\n- Total slots: 21-28 across the full week."},
        {"role": "user", "content": json.dumps(context)}
    ]
    resp = await _call_openrouter(messages, format_json=True)
    return parse_chat_completion(resp)

async def analyze_impact(request: GenerateRequest, timetable: dict) -> str:
    context = {
        "profile": request.profile,
        "timetable": timetable
    }
    messages = [
        {"role": "system", "content": "You are a fitness analyst. Briefly describe the long-term impact of following this specific timetable consistently for 3-6 months. Keep it under 3 sentences."},
        {"role": "user", "content": json.dumps(context)}
    ]
    resp = await _call_openrouter(messages, format_json=False)
    return resp["choices"][0]["message"]["content"]
