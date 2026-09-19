"""Centralized LLM configuration for the gym enrichment agent."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")


def get_llm(temperature: float = 0.2, max_tokens: int = 800) -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for OpenRouter.

    Swap to direct OpenAI by removing base_url and default_headers,
    and setting api_key to your OpenAI key.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model=MODEL_ID,
        temperature=temperature,
        max_tokens=max_tokens,
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "VitroFit Gym Agent",
        },
    )

