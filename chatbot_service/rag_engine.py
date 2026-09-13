# chatbot_service/rag_engine.py
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. Connect to persistent ChromaDB collection
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(name="vitrofit_knowledge")

# 2. Initialize OpenRouter Client (OpenAI compatible)
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

def retrieve_context(query: str, n_results: int = 3) -> str:
    """Finds the most relevant knowledge chunks from ChromaDB."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        documents = results.get("documents", [[]])[0]
        return "\n\n".join(documents) if documents else "No specific context available."
    except Exception as e:
        print(f"ChromaDB retrieval warning: {e}")
        return "No specific context available."

def generate_rag_response(user_query: str) -> str:
    """Retrieves context from ChromaDB and calls the OpenRouter API."""
    context = retrieve_context(user_query)

    system_instruction = (
        "You are the VitroFit AI Fitness Coach. "
        "Answer the user's question accurately using the provided VitroFit context below. "
        "Keep your response concise, energetic, friendly, and helpful. "
        "If the answer is not in the context, answer using general fitness knowledge but mention "
        "that it may vary for specific VitroFit locations."
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