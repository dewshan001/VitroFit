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

    # 3. If query is a simple greeting, skip context retrieval
    COMMON_GREETINGS = {"hi", "hello", "hey", "hola", "yo", "sup", "greetings", "good morning", "good afternoon", "good evening"}
    cleaned_simple = re.sub(r'[^\w\s]', '', query.strip().lower())
    if cleaned_simple in COMMON_GREETINGS:
        return ""

    # 4. Tokenize query and rank chunks by relevance
    query_tokens = set(re.findall(r'\w+', query.lower()))
    if not query_tokens:
        return ""

    scores = []
    for chunk in chunks:
        chunk_words = re.findall(r'\w+', chunk["text"].lower())
        word_counts = Counter(chunk_words)
        # Score based on how many query keywords appear in the chunk
        score = sum(word_counts.get(token, 0) for token in query_tokens)
        scores.append((score, chunk["text"]))

    scores.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [text for score, text in scores[:n_results] if score > 0]

    if not top_chunks:
        return ""

    return "\n\n".join(top_chunks)

def clean_llm_response(text: str) -> str:
    """Removes thinking tags or scratchpad prefixes if the model outputs them."""
    if not text:
        return ""
    # Strip <think>...</think> tags if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # If the response starts with or contains thinking process markers
    if re.search(r"Here['’]s a thinking process|Thinking Process:", text, flags=re.IGNORECASE):
        # 1. Look for explicit Draft Response or Final Response block
        match = re.search(
            r"(?:Draft\s+Response(?:\s*\([^)]*\))?|Final\s+Response)\s*:\s*[\"']?(.*?)(?:[\"']?\s*(?:\n+\s*(?:Check Against|Guidelines|Refine|\d+\.)|$))",
            text,
            flags=re.DOTALL | re.IGNORECASE
        )
        if match and match.group(1).strip():
            candidate = match.group(1).strip()
            if len(candidate) > 5:
                return candidate.strip('"\n\r ')
        
        # 2. Look for any text after double newlines that isn't thinking/analysis
        paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
        for p in reversed(paragraphs):
            if not re.match(r"^(\d+[\.\)]|[-*•]|Analyze|Identify|Check|Determine|Refine|Draft|Here['’]s)", p, flags=re.IGNORECASE):
                if len(p) > 5:
                    return p.strip('"\n\r ')

    return text.strip()

def generate_rag_response(user_query: str) -> str:
    """Retrieves context locally and calls OpenRouter for generation."""
    context = retrieve_context(user_query)

    system_instruction = (
        "You are the VitroFit AI Fitness Coach. Your tone is energetic, friendly, motivating, and helpful. "
        "Answer the user's questions clearly, accurately, and concisely.\n\n"
        "Guidelines:\n"
        "- For casual greetings (e.g., 'hi', 'hello'), greet the user warmly, briefly introduce yourself as the VitroFit Coach, and ask how you can help them crush their fitness goals today.\n"
        "- When VitroFit context is provided, use it to give exact details about memberships, classes, and gym features.\n"
        "- If no specific context is provided, answer using your expert general fitness, workout, and nutrition knowledge.\n"
        "- Keep answers direct and well-structured.\n"
        "- CRITICAL: Output ONLY the final direct message to the user. Do NOT include any 'thinking process', reasoning steps, analysis, scratchpad, or internal monologue (such as 'Here\\'s a thinking process:'). Start immediately with the reply."
    )

    if context.strip():
        user_prompt = f"""[CONTEXT FROM VITROFIT KNOWLEDGE BASE]
{context}

[USER QUESTION]
{user_query}"""
    else:
        user_prompt = user_query

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.5
        )
        raw_reply = response.choices[0].message.content.strip()
        return clean_llm_response(raw_reply)

    except Exception as e:
        return f"OpenRouter API Error: {str(e)}"