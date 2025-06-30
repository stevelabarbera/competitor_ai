
import chromadb
from chromadb.config import Settings
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh import scoring
import subprocess
from pathlib import Path

# Paths
CHROMA_PATH = "./chroma_db"
WHOOSH_INDEX_DIR = "whoosh_index"

# Setup ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_collection(name="competitor_docs")

# Setup Whoosh
ix = open_dir(WHOOSH_INDEX_DIR)
qp = QueryParser("content", schema=ix.schema)

def query_ollama(prompt):
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def semantic_search(question):
    results = collection.query(query_texts=[question], n_results=5)
    docs = results["documents"][0] if results["documents"] else []
    context = "\n\n".join(docs)
    return context

def keyword_search(question):
    with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
        parsed = qp.parse(question)
        results = searcher.search(parsed, limit=5)
        docs = [hit["content"] for hit in results]
        return "\n\n".join(docs)

def ask(question, mode="semantic"):
    try:
        if mode == "keyword":
            context = keyword_search(question)
        else:
            context = semantic_search(question)

        if not context:
            return "❌ No relevant context found."

        final_prompt = f"{context}\n\nAnswer this question based on the context above:\n{question}"
        return query_ollama(final_prompt)
    except Exception as e:
        return f"❌ Error: {e}"
