# chatbot_service/rag_engine.py
import os
import json
import re
from collections import Counter
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

INDEX_PATH = os.path.join(os.path.dirname(__file__), "knowledge_index.json")
RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "vitrofit_knowledge.txt")

# 1. Initialize OpenRouter Client (OpenAI compatible)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing! Set it in your .env file.")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "VitroFit AI Chatbot",
    },
    timeout=30.0,
)


def _load_knowledge_chunks():
    """Loads knowledge chunks from disk once at startup (was re-read on every request)."""
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                chunks = json.load(f)
            if chunks:
                return chunks
        except Exception:
            pass

    # 2. Fallback to raw text file if index isn't created yet
    if os.path.exists(RAW_DATA_PATH):
        with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
            text = f.read()
        raw_chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
        return [{"id": f"c_{i}", "text": c} for i, c in enumerate(raw_chunks)]

    return []


_KNOWLEDGE_CHUNKS = _load_knowledge_chunks()


# Domain synonyms: the knowledge base uses words like "plan"/"membership" but users
# often ask with different words (e.g. "packages") that never literally appear in the
# text, so a pure keyword-overlap match silently returns no context for them.
_QUERY_SYNONYMS = {
    "package": ["plan", "membership", "pricing", "price"],
    "packages": ["plans", "membership", "pricing", "price", "plan"],
    "plan": ["package", "membership"],
    "plans": ["packages", "membership"],
    "membership": ["plan", "package", "pricing"],
    "memberships": ["plans", "packages", "pricing"],
    "price": ["cost", "pricing", "lkr"],
    "prices": ["costs", "pricing", "lkr"],
    "pricing": ["price", "cost", "lkr"],
    "cost": ["price", "pricing", "lkr"],
    "costs": ["prices", "pricing", "lkr"],
    "gym": ["gyms", "facility", "facilities"],
    "class": ["classes", "workout", "session"],
    "workout": ["class", "classes", "exercise", "training"],
}


def _expand_query_tokens(tokens: set) -> set:
    expanded = set(tokens)
    for token in tokens:
        expanded.update(_QUERY_SYNONYMS.get(token, []))
    return expanded


def retrieve_context(query: str, n_results: int = 2) -> str:
    """Finds the most relevant knowledge chunks using local keyword scoring."""
    chunks = _KNOWLEDGE_CHUNKS

    if not chunks:
        return "No specific context available."

    # If query is a simple greeting, skip context retrieval
    COMMON_GREETINGS = {"hi", "hello", "hey", "hola", "yo", "sup", "greetings", "good morning", "good afternoon", "good evening"}
    cleaned_simple = re.sub(r'[^\w\s]', '', query.strip().lower())
    if cleaned_simple in COMMON_GREETINGS:
        return ""

    # Tokenize query (with domain synonyms) and rank chunks by relevance
    query_tokens = _expand_query_tokens(set(re.findall(r'\w+', query.lower())))
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


_THINKING_PREAMBLE_RE = re.compile(
    r"Here['’]s a thinking process|Thinking Process:"
    r"|^\s*I['’]ll (?:draft|structure|now|answer|respond|craft|write)"
    r"|^\s*(?:I will|Let me) (?:draft|structure|now|answer|respond|craft|write)",
    re.IGNORECASE,
)

_META_PARAGRAPH_RE = re.compile(
    r"^(\d+[\.\)]|[-*•]|Analyze|Identify|Check|Determine|Refine|Draft|Here['’]s"
    r"|I['’]ll\b|I will\b|Let me\b|My (?:response|plan|draft|answer) will)",
    re.IGNORECASE,
)


def clean_llm_response(text: str) -> str:
    """Removes thinking tags or scratchpad prefixes if the model outputs them."""
    if not text:
        return ""
    # Strip <think>...</think> tags if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # If the response starts with or contains thinking process markers
    if _THINKING_PREAMBLE_RE.search(text):
        # 1. Look for an explicit Draft/Final (Response) block, however it's labeled
        match = re.search(
            r"(?:Draft(?:\s+Response)?(?:\s*\([^)]*\))?|Final(?:\s+Response)?)\s*:\s*[\"']?\n?(.*?)"
            r"(?:[\"']?\s*(?:\n+\s*(?:Check Against|Self-Correction|Verification|Guidelines|Refine)|\n+\s*\d+[\.\)]\s|$))",
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
            if not _META_PARAGRAPH_RE.match(p):
                if len(p) > 5:
                    return p.strip('"\n\r ')

    return text.strip()


def _build_messages(user_query: str):
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

    return [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt},
    ]


_THINKING_MARKER_RE = re.compile(r"<think>|" + _THINKING_PREAMBLE_RE.pattern, re.IGNORECASE)
_BUFFER_FLUSH_CHARS = 150

# MODEL_ID is a reasoning model that emits its chain-of-thought as regular content
# before the real answer (OpenRouter's reasoning-exclude param has no effect on it).
# A low max_tokens cuts generation off mid-thought before it ever reaches the answer,
# so this needs enough headroom (~600-900 reasoning tokens observed) for it to finish.
_MAX_COMPLETION_TOKENS = 1600


async def generate_rag_response_stream(user_query: str):
    """Retrieves context locally and streams the OpenRouter completion as it's generated.

    Chunks are withheld in a small buffer until we're confident the reply isn't a
    'thinking process' preamble (see clean_llm_response) - if one is detected, we fall
    back to accumulating the full reply, cleaning it, and yielding it as one chunk.
    """
    try:
        stream = await client.chat.completions.create(
            model=MODEL_ID,
            messages=_build_messages(user_query),
            max_tokens=_MAX_COMPLETION_TOKENS,
            temperature=0.5,
            stream=True,
        )
    except Exception as e:
        yield f"OpenRouter API Error: {str(e)}"
        return

    full_text = ""
    buffer = ""
    flushing = False
    thinking_mode = False

    try:
        async for event in stream:
            delta = event.choices[0].delta.content or ""
            if not delta:
                continue
            full_text += delta

            if flushing:
                yield delta
                continue

            if thinking_mode:
                continue

            buffer += delta
            if _THINKING_MARKER_RE.search(buffer):
                thinking_mode = True
                continue

            if len(buffer) >= _BUFFER_FLUSH_CHARS:
                flushing = True
                yield buffer
    except Exception as e:
        if not flushing and not thinking_mode:
            yield f"OpenRouter API Error: {str(e)}"
        return

    if not flushing:
        # Either the whole reply was shorter than the buffer threshold, or a
        # thinking-process preamble was detected - clean the full text before sending.
        cleaned = clean_llm_response(full_text.strip())
        yield cleaned
