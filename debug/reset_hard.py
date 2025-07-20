# reset_hard.py
import shutil
import chromadb
from embedding_config import get_shared_embedding_function
from pathlib import Path

CHROMA_DIR = Path("./chroma_db")
COLLECTION_NAME = "competitor_docs"

if CHROMA_DIR.exists():
    print(f"🧨 Nuking old ChromaDB directory at: {CHROMA_DIR}")
    shutil.rmtree(CHROMA_DIR)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.create_collection(
    name=COLLECTION_NAME,
    embedding_function=get_shared_embedding_function()
)

print(f"✅ Fresh collection '{COLLECTION_NAME}' created with correct embedding function.")