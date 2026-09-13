# chatbot_service/rag_engine.py
import os
import json
import re
from collections import Counter
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

INDEX_PATH = os.path.join(os.path.dirname(__file__), "knowledge_index.json")
RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "vitrofit_knowledge.txt")

# 1. Initialize OpenRouter Client (OpenAI compatible)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing! Set it in your .env file.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "VitroFit AI Chatbot",
    }
)

def retrieve_context(query: str, n_results: int = 2) -> str:
    """Finds the most relevant knowledge chunks using local keyword scoring."""
    # 1. Load from index if available
    chunks = []
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        except Exception:
            pass

    # 2. Fallback to raw text file if index isn't created yet
    if not chunks and os.path.exists(RAW_DATA_PATH):
        with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
            text = f.read()
        raw_chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
        chunks = [{"id": f"c_{i}", "text": c} for i, c in enumerate(raw_chunks)]

    if not chunks:
        return "No specific context available."

    # 3. Tokenize query and rank chunks by relevance
    query_tokens = set(re.findall(r'\w+', query.lower()))
    if not query_tokens:
        return "\n\n".join(c["text"] for c in chunks[:n_results])

    scores = []
    for chunk in chunks:
        chunk_words = re.findall(r'\w+', chunk["text"].lower())
        word_counts = Counter(chunk_words)
        # Score based on how many query keywords appear in the chunk
        score = sum(word_counts.get(token, 0) for token in query_tokens)
        scores.append((score, chunk["text"]))

    scores.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [text for score, text in scores[:n_results] if score > 0]

    # If no specific keyword matched, include the first chunks as baseline context
    if not top_chunks:
        top_chunks = [c["text"] for c in chunks[:n_results]]

    return "\n\n".join(top_chunks)

def generate_rag_response(user_query: str) -> str:
    """Retrieves context locally and calls OpenRouter for generation."""
    context = retrieve_context(user_query)

    system_instruction = (
        "You are the VitroFit AI Fitness Coach. "
        "Answer the user's question accurately using the provided VitroFit context below. "
        "Keep your response concise, energetic, friendly, and helpful. "
        "If the answer is not in the context, answer using general fitness knowledge."
    )

    user_prompt = f"""[CONTEXT FROM VITROFIT KNOWLEDGE BASE]
{context}

[USER QUESTION]
{user_query}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"OpenRouter API Error: {str(e)}"