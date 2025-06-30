# debug_collection.py
import chromadb
from embedding_config import get_competitor_collection

client = chromadb.PersistentClient(path="./chroma_db")
collection = get_competitor_collection(client)

print(f"📊 Document count: {collection.count()}")

docs = collection.get(limit=5)
documents = docs.get("documents", [])

if not documents:
    print("⚠️ No documents found in the collection.")
else:
    for i, doc in enumerate(documents):
        print(f"\n📝 Doc {i+1}:")
        print(doc[:500])  # Preview first 500 characters