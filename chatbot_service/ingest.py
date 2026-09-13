# chatbot_service/ingest.py
import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

# 1. Initialize persistent ChromaDB storage
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# 2. Create or get collection
collection = client.get_or_create_collection(
    name="vitrofit_knowledge",
    metadata={"hnsw:space": "cosine"} # Cosine similarity for semantic search
)

def run_ingestion():
    file_path = os.path.join(os.path.dirname(__file__), "data", "vitrofit_knowledge.txt")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split documents by section or double newlines
    raw_chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    
    print(f"Found {len(raw_chunks)} knowledge chunks to ingest...")

    ids = [f"chunk_{i}" for i in range(len(raw_chunks))]
    metadatas = [{"source": "vitrofit_knowledge.txt", "chunk_id": i} for i in range(len(raw_chunks))]

    # ChromaDB embeds automatically using its built-in MiniLM embedding function
    collection.upsert(
        documents=raw_chunks,
        ids=ids,
        metadatas=metadatas
    )

    print(f"Ingested {len(raw_chunks)} chunks into ChromaDB successfully at '{CHROMA_DATA_PATH}'.")

if __name__ == "__main__":
    run_ingestion()