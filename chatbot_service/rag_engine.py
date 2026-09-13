# chatbot_service/rag_engine.py
import os
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Connect to the persistent ChromaDB collection
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(name="vitrofit_knowledge")

# Initialize Gemini Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def retrieve_context(query: str, n_results: int = 3) -> str:
    """Finds the most semantically relevant text chunks from ChromaDB."""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    documents = results.get("documents", [[]])[0]
    return "\n\n".join(documents) if documents else "No specific context found."

def generate_rag_response(user_query: str) -> str:
    """Combines retrieved VitroFit context with Gemini LLM generation."""
    # 1. Retrieve relevant facts from vector store
    context = retrieve_context(user_query)

    # 2. Build the augmented prompt
    rag_prompt = f"""
You are the official VitroFit AI Fitness Assistant.
Answer the user's question accurately using ONLY the following verified context from VitroFit.
If the answer is not in the context, politely state that you do not have that specific information, but offer general fitness advice if appropriate.

[CONTEXT FROM VITROFIT KNOWLEDGE BASE]
{context}

[USER QUESTION]
{user_query}
"""

    # 3. Call Gemini
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=rag_prompt,
        config=types.GenerateContentConfig(
            temperature=0.3, # Lower temperature = higher factual accuracy
            max_output_tokens=500
        )
    )

    return response.text or "I apologize, but I couldn't process your request."