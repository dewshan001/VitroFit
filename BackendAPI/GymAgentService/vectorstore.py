"""Vector store for RAG — stores enriched gym data for similarity lookups."""

import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_gym_data")


def _get_embeddings() -> OpenAIEmbeddings:
    """Get embedding model via OpenRouter or OpenAI."""
    return OpenAIEmbeddings(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="openai/text-embedding-3-small",
    )


def get_vectorstore() -> Chroma:
    """Get or create the ChromaDB vector store for gym enrichment data."""
    return Chroma(
        collection_name="gym_enrichments",
        embedding_function=_get_embeddings(),
        persist_directory=_CHROMA_DIR,
    )


def store_gym_enrichment(
    place_id: str,
    name: str,
    address: str | None,
    equipment: list[str],
    classes: list[str],
) -> None:
    """Store a gym's enrichment result in the vector store for future RAG lookups."""
    text = (
        f"Gym: {name}\n"
        f"Address: {address or 'unknown'}\n"
        f"Equipment: {', '.join(equipment)}\n"
        f"Classes: {', '.join(classes)}"
    )
    doc = Document(
        page_content=text,
        metadata={
            "place_id": place_id,
            "name": name,
            "address": address or "",
        },
    )
    vs = get_vectorstore()
    vs.add_documents([doc], ids=[place_id])


def find_similar_gyms(gym_name: str, city: str, k: int = 3) -> list[Document]:
    """Find similar previously-enriched gyms by name/location."""
    vs = get_vectorstore()
    try:
        results = vs.similarity_search(f"{gym_name} {city}", k=k)
        return results
    except Exception:
        return []

