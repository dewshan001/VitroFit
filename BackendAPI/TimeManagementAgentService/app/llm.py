import json
import httpx
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from .schemas import GenerateRequest, Timetable

class PlannerError(RuntimeError):
    pass

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openrouter_api_key: str = ""
    openrouter_model: str = ""

def parse_chat_completion(payload: dict) -> Timetable:
    try:
        choice = payload["choices"][0]
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise PlannerError("MODEL_OUTPUT_EMPTY")
        return Timetable.model_validate_json(content)
    except PlannerError:
        raise
    except ValidationError:
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
                "max_tokens": 1500,
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
        {"role": "system", "content": "You are a time management scheduler. Output strictly JSON matching the outputSchema. Assign a startTime and endTime for each day in the provided plan based on typical user preferences or standard times (e.g. 18:00 to 19:30). Ensure durationMinutes matches the plan."},
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
