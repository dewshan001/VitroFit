# chatbot_service/ingest.py
import os
import json
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "knowledge_index.json")

def run_ingestion():
    file_path = os.path.join(DATA_DIR, "vitrofit_knowledge.txt")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split documents by sections or double newlines
    raw_chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    
    print(f"Indexing {len(raw_chunks)} knowledge chunks from '{file_path}'...")

    chunks_data = []
    for i, chunk in enumerate(raw_chunks):
        words = re.findall(r'\w+', chunk.lower())
        chunks_data.append({
            "id": f"chunk_{i}",
            "text": chunk,
            "keywords": list(set(words))
        })

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully indexed {len(chunks_data)} chunks to '{INDEX_PATH}'.")
    print("Complete! Zero external model downloads required.")

if __name__ == "__main__":
    run_ingestion()