# search_engine/enhanced_search_engine.py
import os
import argparse
from pathlib import Path
import chromadb
import logging
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from embedding_config import get_competitor_collection
import subprocess
import json
import traceback
from typing import List, Tuple
from chunk_filtering.quality_filter import QualityFilter

ROOT_DIR = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = ROOT_DIR / "chroma_db"
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
FULL_CONTEXT_FILE = ROOT_DIR / "full_context.txt"
MODEL_CONFIG_FILE = ROOT_DIR / "config_model.txt"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_model_name():
    try:
        return MODEL_CONFIG_FILE.read_text().strip()
    except Exception as e:
        logger.exception(f"⚠️ Could not read model config file: {e}")
        return "llama3:instruct"

client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
collection = get_competitor_collection(client)
logger.info(f"🔍 Collection 'competitor_docs' has {collection.count()} chunks.")
ix = open_dir(str(WHOOSH_INDEX_DIR))

def query_ollama(prompt: str) -> str:
    model = get_model_name()
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def llm_rerank_chunks(question: str, chunks: List[Tuple[str, dict]], top_k: int = 5) -> List[Tuple[str, dict]]:
    if len(chunks) <= top_k:
        return chunks

    chunk_list = "\n".join([f"[{i}] {chunk[:200]}..." for i, (chunk, _) in enumerate(chunks)])
    rerank_prompt = f"""
You are helping to find the most relevant information to answer a question.

Question: {question}

Below are numbered text chunks. Return ONLY the numbers (0-{len(chunks)-1}) of the {top_k} most relevant chunks, in order of relevance. 
Separate numbers with commas (e.g., "2,5,1,8,3").

Chunks:
{chunk_list}

Most relevant chunk numbers:
"""
    try:
        response = query_ollama(rerank_prompt)
        logger.info(f"🔁 Rerank response: {response}")
        indices = [int(x.strip()) for x in response.split(',') if x.strip().isdigit()]
        indices = [i for i in indices if 0 <= i < len(chunks)][:top_k]
        return [chunks[i] for i in indices] if indices else chunks[:top_k]
    except Exception as e:
        logger.exception(f"⚠️ Reranking failed: {e}, using original order")
        return chunks[:top_k]

def search_semantic_enhanced(question: str, n_results: int = 10, source_filter: str = None, use_reranking: bool = True, top_k: int = 5):
    query_params = {
        "query_texts": [question],
        "n_results": n_results
    }
    if source_filter:
        query_params["where"] = {"source": source_filter}

    results = collection.query(**query_params)
    logger.info(f"📦 Raw Chroma query result: {json.dumps(results, indent=2, default=str)}")

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents or not metadatas:
        return []

    chunk_meta_pairs = list(zip(documents, metadatas))

    quality_filter = QualityFilter(min_words=50)
    filtered_pairs = []
    for chunk, meta in chunk_meta_pairs:
        if chunk.strip() and len(chunk.split()) >= quality_filter.min_words:
            if not any(signal in chunk.lower() for signal in quality_filter.boilerplate_signals):
                cleaned = "\n".join(line.strip() for line in chunk.splitlines() if line.strip())
                filtered_pairs.append((cleaned, meta))

    if not filtered_pairs:
        return []

    return llm_rerank_chunks(question, filtered_pairs, top_k=top_k) if use_reranking else filtered_pairs

def ask_enhanced(question: str, mode: str = "semantic", source_filter: str = None, 
                company: str = None, use_reranking: bool = True, n_results: int = 10, 
                top_k: int = 5) -> str:
    try:
        if mode == "semantic":
            docs = search_semantic_enhanced(question, n_results, source_filter, use_reranking, top_k)
            if not docs:
                return "No relevant semantic documents found in your internal data."
            context = "\n\n".join(f"[Source: {meta.get('source', 'unknown')}]\n{chunk}" for chunk, meta in docs)
            context_source = "semantic search of your internal documents"

        else:
            return "❌ Only semantic mode supported in this version."

        final_prompt = f"""
You are a competitive intelligence assistant specializing in cybersecurity vendors.

CRITICAL INSTRUCTIONS:
1. ONLY use information from the provided context below
2. Do NOT use your general knowledge about companies or products
3. If the context doesn't contain the answer, respond: "This information is not available in the current internal documents."
4. Always cite your sources using the format [source_name]
5. Be specific and factual - avoid speculation
6. Focus on competitive intelligence insights, pricing, and product comparisons

CONTEXT SOURCE: {context_source}

--- START OF INTERNAL CONTEXT ---
{context}
--- END OF INTERNAL CONTEXT ---

QUESTION: {question}

ANSWER (based only on the context above):
"""
        logger.info(f"🔍 Using {mode} mode with {len(context)} characters of context")
        return query_ollama(final_prompt)

    except Exception as e:
        logger.exception(f"❌ Error during {mode} search: {e}")
        return f"❌ Error during {mode} search: {e}"

def debug_collection_content(question: str = "cybersecurity", n_results: int = 5):
    results = collection.query(query_texts=[question], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    print(f"🔍 DEBUG: Found {len(docs)} docs:")
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        print(f"--- Result {i+1} ---\nSource: {meta.get('source', 'unknown')}\nChunk: {doc[:200]}...\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument("--mode", default="semantic", choices=["semantic"], help="Search mode")
    args = parser.parse_args()

    print(f"🔧 Using embedding model: {get_model_name()}")
    answer = ask_enhanced(
        question=args.question,
        mode=args.mode
    )
    print(f"\n💬 Answer:\n{answer}")
