"""Centralized LLM configuration for the gym enrichment agent."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct")


def get_llm(temperature: float = 0.2, max_tokens: int = 800) -> ChatOpenAI:
    """Create a ChatOpenAI instance for the agent's LLM calls.

    Uses NVIDIA NIM (build.nvidia.com) when NVIDIA_API_KEY is set, since it has
    its own quota independent of OpenRouter's shared free-tier daily limit.
    Falls back to OpenRouter otherwise.
    """
    if NVIDIA_API_KEY:
        return ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=NVIDIA_API_KEY,
            model=NVIDIA_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if not OPENROUTER_API_KEY:
        raise RuntimeError("Neither NVIDIA_API_KEY nor OPENROUTER_API_KEY is set in .env")

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model=OPENROUTER_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "VitroFit Gym Agent",
        },
    )

