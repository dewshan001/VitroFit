# test.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

if not OPENROUTER_API_KEY:
    raise ValueError("Error: OPENROUTER_API_KEY is missing! Check your .env file.")

# OpenRouter is 100% compatible with the standard OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:5173",  # Optional: For OpenRouter rankings
        "X-Title": "VitroFit Chatbot",            # Optional: Shows in your OpenRouter dashboard
    }
)

print(f"Connecting to OpenRouter model: {MODEL_ID}...")

try:
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": "You are the VitroFit AI Coach."},
            {"role": "user", "content": "What is a good 10-minute warmup for leg day?"}
        ],
        max_tokens=150,
        temperature=0.7
    )

    print("\n--- Response from AI ---")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"\nError: {e}")