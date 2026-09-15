# GymAgentService/enrichment_agent.py
import os
import json
import re
import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing! Set it in your .env file.")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "VitroFit Gym Agent",
    },
    timeout=30.0,
)

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VitroFitGymAgent/1.0; +http://localhost)"
}
_MAX_SITE_TEXT_CHARS = 4000


async def _scrape_website_text(url: str) -> str | None:
    """Best-effort fetch of visible text from a gym's website. Returns None on any failure."""
    if not url:
        return None
    if not url.startswith("http"):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(headers=_HTTP_HEADERS, timeout=8.0, follow_redirects=True) as http_client:
            resp = await http_client.get(url)
            resp.raise_for_status()
    except Exception:
        return None

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:_MAX_SITE_TEXT_CHARS] if text else None
    except Exception:
        return None


_JSON_BLOCK_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _extract_list(data: dict, key_substring: str) -> list[str]:
    """Some free models drift from the exact key name (e.g. 'classes_and_functions'
    instead of 'classes') even when the schema is spelled out, so match loosely on
    any key containing the expected substring rather than an exact key lookup."""
    for key, value in data.items():
        if key_substring in key.lower() and isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip() and str(x).strip() != "..."][:20]
    return []


def _parse_llm_json(raw: str) -> dict:
    """Some free reasoning models emit their chain-of-thought as plain text before the
    real answer, and that thought often restates the requested JSON shape verbatim.
    So instead of taking the first JSON-looking block, scan all of them (after
    stripping markdown fences) and take the last one that parses with real values.
    """
    cleaned = (raw or "").replace("```json", "").replace("```", "")
    candidates = _JSON_BLOCK_RE.findall(cleaned)
    for candidate in reversed(candidates):
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        equipment = _extract_list(data, "equip")
        classes = _extract_list(data, "class") or _extract_list(data, "function")
        if equipment or classes:
            return {"equipment": equipment, "classes": classes}
    return {"equipment": [], "classes": []}


async def enrich_gym(name: str, address: str | None, website: str | None) -> dict:
    """Returns {"source": "ai-scraped"|"ai-generic", "equipment": [...], "classes": [...]}."""
    site_text = await _scrape_website_text(website) if website else None

    if site_text:
        source = "ai-scraped"
        user_prompt = (
            f"Gym name: {name}\n"
            f"Address: {address or 'unknown'}\n\n"
            f"Text scraped from the gym's own website:\n{site_text}\n\n"
            "From this text, list the gym equipment mentioned (e.g. treadmills, squat racks, "
            "free weights, cable machines, pool) and the classes/functions offered "
            "(e.g. yoga, CrossFit, spin, personal training, swimming). "
            "Only include items actually mentioned or clearly implied by the text - do not invent."
        )
    else:
        source = "ai-generic"
        user_prompt = (
            f"Gym name: {name}\n"
            f"Address: {address or 'unknown'}\n\n"
            "No website text is available for this gym. Based only on the name/address and "
            "typical equipment/classes for this kind of fitness facility, give a brief, generic "
            "best-guess list. Keep it short and mark it as a guess by only including very common items."
        )

    system_instruction = (
        "You are a data-extraction assistant for a fitness app. "
        'Respond with ONLY a single JSON object, e.g. {"equipment": ["treadmill", "squat rack"], '
        '"classes": ["yoga", "spin"]}, and nothing else - no prose, no thinking process, no markdown fences.'
    )

    try:
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        return {"source": source, "equipment": [], "classes": [], "error": str(e)}

    parsed = _parse_llm_json(raw)
    return {"source": source, **parsed}
