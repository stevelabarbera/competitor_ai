# reset_collection.py
import chromadb
from chromadb.config import Settings
from ollama_embed import OllamaEmbeddingFunction  # make sure this exists

# Use PersistentClient if you're persisting data
client = chromadb.PersistentClient(path="./chroma_db")

# Delete the old collection (if it exists)
try:
    client.delete_collection("competitor_docs")
    print("✅ Deleted old collection: competitor_docs")
except Exception as e:
    print(f"⚠️ Could not delete collection (might not exist): {e}")

# Recreate collection with proper embedding function
embedding_function = OllamaEmbeddingFunction()
collection = client.get_or_create_collection(
    name="competitor_docs",
    embedding_function=embedding_function
)
print("✅ Recreated collection with correct embedding function")

