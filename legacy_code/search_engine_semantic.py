import chromadb
from chromadb.config import Settings
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
import subprocess

# Paths
CHROMA_PATH = "./chroma_db"
WHOOSH_INDEX_DIR = "whoosh_index"

# Connect to ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_collection(name="competitor_docs")

# Connect to Whoosh
ix = open_dir(WHOOSH_INDEX_DIR)

def query_ollama(prompt, model="llama3"):
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def search_semantic(question, top_k=5):
    results = collection.query(query_texts=[question], n_results=top_k)
    return results["documents"][0] if results["documents"] else []

def search_keyword(question, top_k=5):
    with ix.searcher() as searcher:
        parser = QueryParser("content", schema=ix.schema)
        query = parser.parse(question)
        results = searcher.search(query, limit=top_k)
        return [hit["content"] for hit in results]

def build_prompt(context, question):
    return f"{context}/n/nAnswer this question based on the context above:/n/n{question}"

def ask(question, mode="semantic", top_k=5):
    if mode == "semantic":
        docs = search_semantic(question, top_k)
    elif mode == "keyword":
        docs = search_keyword(question, top_k)
    elif mode == "hybrid":
        # Combine semantic and keyword (remove duplicates)
        semantic_docs = search_semantic(question, top_k)
        keyword_docs = search_keyword(question, top_k)
        docs = list(dict.fromkeys(semantic_docs + keyword_docs))
    elif mode == "full":
        with open("full_context.txt", "r") as f:
            docs = [f.read()]
    else:
        return f"❌ Unsupported mode: {mode}"

    context = "\n\n".join(docs)
    prompt = build_prompt(context, question)
    return query_ollama(prompt)