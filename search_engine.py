import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from embedding_config import get_competitor_collection


import subprocess

# === Configuration ===
ROOT_DIR = Path(__file__).resolve().parent
CHROMA_DB_PATH = ROOT_DIR / "chroma_db"
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
FULL_CONTEXT_FILE = ROOT_DIR / "full_context.txt"
MODEL_CONFIG_FILE = ROOT_DIR / "config_model.txt"

# === Load model name dynamically ===
def get_model_name():
    try:
        return MODEL_CONFIG_FILE.read_text().strip()
    except Exception as e:
        print(f"⚠️ Could not read model config file: {e}")
        return "llama3"  # fallback default

# === Load vector (semantic) search collection ===
client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
collection = get_competitor_collection(client)

# === Load Whoosh keyword index ===
ix = open_dir(str(WHOOSH_INDEX_DIR))

def query_ollama(prompt: str) -> str:
    """Calls Ollama using the dynamically selected model."""
    model = get_model_name()
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def search_semantic(question: str, n_results: int = 5):
    results = collection.query(query_texts=[question], n_results=n_results)
    return results.get("documents", [[]])[0]

def search_keyword(question: str, n_results: int = 5):
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        query = parser.parse(question)
        hits = searcher.search(query, limit=n_results)
        return [hit["content"] for hit in hits]

def ask(question: str, mode: str = "semantic") -> str:
    """Routes the question through the selected search mode."""
    try:
        if mode == "semantic":
            docs = search_semantic(question)
            if not docs:
                return "No relevant semantic documents found."
            context = "\n\n".join(docs)

        elif mode == "keyword":
            docs = search_keyword(question)
            if not docs:
                return "No relevant keyword documents found."
            context = "\n\n".join(docs)

        elif mode == "hybrid":
            sem_docs = search_semantic(question)
            key_docs = search_keyword(question)
            all_docs = list({doc for doc in sem_docs + key_docs if doc})
            if not all_docs:
                return "No relevant documents found from either method."
            context = "\n\n".join(all_docs)

        elif mode == "full":
            try:
                context = FULL_CONTEXT_FILE.read_text(encoding="utf-8")
            except Exception as e:
                return f"❌ Failed to load full context: {e}"

        else:
            return "❌ Invalid mode selected."

        final_prompt = f"""
        You are a competitive intelligence assistant analyzing cybersecurity vendors.

        You will be given a large block of text that includes notes, datasheets, and summaries from various documents.

        Important Instructions:
        - Only answer questions based on the provided content.
        - Do **not** rely on prior knowledge.
        - If the answer cannot be found in the content, say: "Not enough information available in the current context."
        - Provide the document name(s) in square brackets as citations. For example: [censys_com/content.txt]
        - Be brief and factual. Avoid speculation or hallucination.

        --- START OF CONTEXT ---
        {context}
        --- END OF CONTEXT ---

        Answer the following question:
        {question}
        """
        print("🔍 FINAL PROMPT:\n", final_prompt[:2000], "...\n")  # optional truncate for debugging

        return query_ollama(final_prompt)

    except Exception as e:
        return f"❌ Error during {mode} search: {e}"
