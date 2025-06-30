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

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

client = chromadb.PersistentClient(path="./chroma_db")
collection_name = "competitor_docs"

try:
    client.delete_collection(collection_name)
    print(f"🗑️ Deleted old collection: {collection_name}")
except Exception:
    print(f"ℹ️ Collection {collection_name} did not exist. Continuing...")

embedding_function = OllamaEmbeddingFunction(model_name="nomic-embed-text")
client.create_collection(name=collection_name, embedding_function=embedding_function)
print(f"✅ Recreated collection: {collection_name}")
