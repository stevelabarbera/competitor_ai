import chromadb
from embedding_config import get_competitor_collection
from chunker import chunk_text  # Ensure this matches your actual tokenizer logic

# === Setup ===
client = chromadb.PersistentClient(path="./chroma_db")
collection = get_competitor_collection(client)

def print_collection():
    
# === Optional cleanup ===
print("🧹 Removing previous 'cyberboing_test' documents...")
try:
    existing = collection.get(include=["ids"], where={"source": "cyberboing_test.txt"})
    ids_to_delete = existing["ids"]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        print(f"🗑️ Deleted {len(ids_to_delete)} previous test chunks.")
except Exception as e:
    print(f"⚠️ Cleanup failed or unnecessary: {e}")

# === Test input ===
test_text = """
    Cyberboing™ visibility mesh 2048-mode.
    Cyberboing's ASM platform claims to find 2x more vulnerabilities than its competitors.
    It raised $20 million in its first week to disrupt attack surface management.
"""

# === Chunk and inject ===
chunks = chunk_text(test_text, chunk_size=512, overlap=64)

for i, chunk in enumerate(chunks):
    doc_id = f"cyberboing_test_{i}"
    collection.add(
        documents=[chunk],
        metadatas=[{"source": "cyberboing_test.txt"}],
        ids=[doc_id]
    )

print(f"✅ Injected {len(chunks)} Cyberboing test chunk(s) into ChromaDB.")
