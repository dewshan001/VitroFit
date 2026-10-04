# DietPlanService/src/models/llm_client.py
"""Centralised NVIDIA NIM LLM configuration and the single low-level model call
used by the meal-generation tools (src/tools/tools.py)."""
import asyncio
import logging
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

from src.prompts.system_prompts import SYSTEM_INSTRUCTION
from src.utils.logger import log_event

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
PRIMARY_MODEL = os.getenv("NVIDIA_MODEL_PRIMARY", "meta/llama-3.2-11b-vision-instruct")
FALLBACK_MODEL = os.getenv("NVIDIA_MODEL_FALLBACK", "meta/llama-3.2-11b-vision-instruct")

if not NVIDIA_API_KEY:
    log_event("NVIDIA_API_KEY is missing - set it in your .env file", level=logging.WARNING)

client = AsyncOpenAI(api_key=NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")

CALL_TIMEOUT_SECONDS = 70  # measured live-call latency against the real NVIDIA
# endpoint (meta/llama-3.2-11b-vision-instruct) ranged 65-118s on success -
# raised from 40s, which was cutting off calls that were still in progress
# and about to succeed.


async def call_model(model_id: str, prompt: str, system_instruction: str = SYSTEM_INSTRUCTION) -> str:
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.6,
        ),
        timeout=CALL_TIMEOUT_SECONDS,
    )
    return response.choices[0].message.content or ""
