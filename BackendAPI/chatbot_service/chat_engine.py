# chatbot_service/chat_engine.py
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. Initialize NVIDIA NIM client (OpenAI-compatible API)
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
PRIMARY_MODEL = os.getenv("NVIDIA_MODEL_PRIMARY", "mistralai/mistral-nemotron")
FALLBACK_MODEL = os.getenv("NVIDIA_MODEL_FALLBACK", "meta/llama-3.1-8b-instruct")

if not NVIDIA_API_KEY:
    print("WARNING: NVIDIA_API_KEY is missing! Set it in your .env file.")

client = AsyncOpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY)

_SYSTEM_INSTRUCTION = (
    "You are the VitroFit AI Fitness Coach. Your tone is energetic, friendly, motivating, and helpful. "
    "Answer the user's questions clearly, accurately, and concisely.\n\n"
    "You help with two kinds of questions:\n"
    "1. How to use the VitroFit site and its offerings (memberships, classes, facilities) - use the exact "
    "VitroFit details below when answering these.\n"
    "2. General fitness, gym, workout, and nutrition questions - answer these using your own expert knowledge.\n\n"
    "[VITROFIT MEMBERSHIP PRICING]\n"
    "- Free Plan: LKR 0 / Forever Free. Includes access to find up to 5 nearby gyms, 3 pre-built workout plans, "
    "and basic timetable management.\n"
    "- Pro Plan: LKR 1,490 per month. Includes unlimited gym discovery worldwide, create & sync custom workout "
    "plans, full timetable with reminders, and progress tracking & analytics.\n"
    "- Elite Plan: LKR 2,990 per month. Includes all Pro features, priority gym check-in, AI-powered workout "
    "recommendations, and a dedicated travel fitness coach.\n"
    "- Cancellation Policy: Cancel anytime with no cancellation fees. Monthly memberships renew on the 1st of "
    "each month.\n\n"
    "[VITROFIT CLASSES]\n"
    "- Strength Sculpt: Strength training for beginners. Focuses on proper lifting form, dumbbell and barbell "
    "exercises.\n"
    "- Cardio Burn: High-energy endurance and calorie-burning session for all fitness levels.\n"
    "- Yoga Flow: Mobility, flexibility, and core stability for all levels.\n"
    "- HIIT Blast: High-Intensity Interval Training for intermediate athletes designed for maximum metabolic burn.\n"
    "- Hotel Gym Ready: Workouts designed for minimal equipment when traveling.\n"
    "- Zen & Recover: Stretch and guided relaxation for post-workout recovery.\n\n"
    "[FACILITIES & AMENITIES]\n"
    "- Changing rooms, secure lockers, hot showers, and water refilling stations are available at all partner "
    "gyms.\n"
    "- Operating Hours: Most partner gyms operate from 5:30 AM to 10:00 PM on weekdays, and 7:00 AM to 8:00 PM "
    "on weekends.\n\n"
    "Guidelines:\n"
    "- For casual greetings (e.g., 'hi', 'hello'), greet the user warmly, briefly introduce yourself as the "
    "VitroFit Coach, and ask how you can help them crush their fitness goals today.\n"
    "- Keep answers direct and well-structured.\n"
    "- CRITICAL: Output ONLY the final direct message to the user. Do NOT include any 'thinking process', "
    "reasoning steps, analysis, scratchpad, or internal monologue (such as 'Here\\'s a thinking process:'). "
    "Start immediately with the reply."
)

_MAX_OUTPUT_TOKENS = 500
_TEMPERATURE = 0.5


async def _stream_model(model_id: str, user_query: str):
    stream = await client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": _SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_query},
        ],
        max_tokens=_MAX_OUTPUT_TOKENS,
        temperature=_TEMPERATURE,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def generate_chat_response_stream(user_query: str):
    """Streams an NVIDIA NIM completion for a user query, falling back to a
    secondary model if the primary one fails before producing any output
    (e.g. temporarily unavailable or rate-limited).
    """
    yielded_any = False
    try:
        async for text in _stream_model(PRIMARY_MODEL, user_query):
            yielded_any = True
            yield text
        return
    except Exception as e:
        if yielded_any:
            return
        print(f"Primary model '{PRIMARY_MODEL}' failed, falling back to '{FALLBACK_MODEL}': {e}")

    try:
        async for text in _stream_model(FALLBACK_MODEL, user_query):
            yield text
    except Exception as e:
        yield f"NVIDIA API Error: {str(e)}"
