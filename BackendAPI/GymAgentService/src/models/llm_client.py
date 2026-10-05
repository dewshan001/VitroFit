"""Centralized LLM configuration for the gym enrichment agent."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.utils.logger import get_handler

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct")

# "nvidia" | "openrouter" | "" (auto: NVIDIA when its key is set, otherwise OpenRouter).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

# gpt-oss models think before answering; "low" cut latency roughly in half on this agent's prompts
# (about 250 instead of 670 output tokens) with the same JSON quality. low | medium | high | "" = default.
NVIDIA_REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low").strip().lower() or None

# Reasoning models can spend the whole token budget thinking and return an empty answer
# (finish_reason=length). On OpenRouter, "off" disables thinking (fastest, reliable for this agent's
# extraction and JSON tasks); low | medium | high set an effort instead (low was not reliable); "" sends nothing.
OPENROUTER_REASONING = os.getenv("OPENROUTER_REASONING", "off").strip().lower()


def _openrouter_reasoning() -> dict | None:
    if not OPENROUTER_REASONING:
        return None
    if OPENROUTER_REASONING in ("off", "none", "false"):
        return {"reasoning": {"enabled": False}}
    return {"reasoning": {"effort": OPENROUTER_REASONING}}


def get_llm(temperature: float = 0.2, max_tokens: int = 800) -> ChatOpenAI:
    """Create a ChatOpenAI instance for the agent's LLM calls.

    Uses NVIDIA NIM (build.nvidia.com) when NVIDIA_API_KEY is set, since it has
    its own quota independent of OpenRouter's shared free-tier daily limit.
    Falls back to OpenRouter otherwise.

    Every model built here logs its calls through GymAgentLoggingHandler (timing, tokens, errors;
    never prompts or replies), which covers the four workflow agents and the legacy enrichment path.
    """
    use_nvidia = LLM_PROVIDER == "nvidia" or (LLM_PROVIDER != "openrouter" and bool(NVIDIA_API_KEY))
    if use_nvidia and NVIDIA_API_KEY:
        return ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=NVIDIA_API_KEY,
            model=NVIDIA_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=NVIDIA_REASONING_EFFORT if "gpt-oss" in NVIDIA_MODEL else None,
            callbacks=[get_handler()],
        )

    if not OPENROUTER_API_KEY:
        raise RuntimeError("Neither NVIDIA_API_KEY nor OPENROUTER_API_KEY is set in .env")

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model=OPENROUTER_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        callbacks=[get_handler()],
        extra_body=_openrouter_reasoning(),
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "VitroFit Gym Agent",
        },
    )

