import os
import argparse
import subprocess
import json
import traceback
from pathlib import Path
from typing import List, Tuple

import chromadb
from whoosh.index import open_dir
from whoosh.query import And, Term
from whoosh.qparser import QueryParser

from chunk_filtering.quality_filter import QualityFilter
from embedding_config import get_competitor_collection
from utils.extract_company import extract_company_name, normalize_company_name

ROOT_DIR = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = ROOT_DIR / "chroma_db"
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
FULL_CONTEXT_FILE = ROOT_DIR / "full_context.txt"
MODEL_CONFIG_FILE = ROOT_DIR / "config_model.txt"

client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
ix = open_dir(str(WHOOSH_INDEX_DIR))

def get_model_name():
    try:
        return MODEL_CONFIG_FILE.read_text().strip()
    except Exception as e:
        print(f"\u26a0\ufe0f Could not read model config file: {e}")
        return "llama3:instruct"

def query_ollama(prompt: str) -> str:
    model = get_model_name()
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def get_target_collection(client, question: str):
    company = extract_company_name(question)
    if company:
        normalized = normalize_company_name(company)
        try:
            return client.get_collection(name=f"docs_{normalized}")
        except:
            print(f"\u26a0\ufe0f No collection for '{normalized}', using fallback.")
    return client.get_collection(name="competitor_docs")

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
        indices = [int(x.strip()) for x in response.split(',') if x.strip().isdigit()]
        indices = [i for i in indices if 0 <= i < len(chunks)][:top_k]
        return [chunks[i] for i in indices] if indices else chunks[:top_k]
    except Exception as e:
        print(f"\u26a0\ufe0f Reranking failed: {e}, using original order")
        return chunks[:top_k]

def search_semantic_enhanced(question: str, collection, n_results: int = 10, source_filter: str = None, use_reranking: bool = True, top_k: int = 5):
    query_params = {"query_texts": [question], "n_results": n_results}
    if source_filter:
        query_params["where"] = {"source": source_filter}

    results = collection.query(**query_params)
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    chunk_meta_pairs = [(doc, meta) for doc, meta in zip(documents, metadatas) if doc and meta]
    quality_filter = QualityFilter(min_words=50)
    filtered = [("\n".join(line.strip() for line in chunk.splitlines() if line.strip()), meta)
                for chunk, meta in chunk_meta_pairs
                if len(chunk.split()) >= quality_filter.min_words and not any(signal in chunk.lower() for signal in quality_filter.boilerplate_signals)]

    return llm_rerank_chunks(question, filtered, top_k=top_k) if use_reranking else filtered

def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        try:
            content_query = parser.parse(question.replace("?", "").replace(",", " "))
        except:
            content_query = parser.parse(f'"{question}"')

        final_query = And([content_query, Term("company", company)]) if company else content_query
        hits = searcher.search(final_query, limit=n_results)
        chunks = [hit["content"] for hit in hits]

        quality_filter = QualityFilter(min_words=50)
        return quality_filter.filter(chunks)

def ask_enhanced(question: str, mode: str = "semantic", source_filter: str = None, company: str = None, use_reranking: bool = True, n_results: int = 10, top_k: int = 5) -> str:
    try:
        collection = get_target_collection(client, question)
        if mode == "semantic":
            docs = search_semantic_enhanced(question, collection, n_results, source_filter, use_reranking, top_k)
            if not docs:
                return "No relevant semantic documents found."
            context = "\n\n".join(chunk for chunk, _ in docs)
            context_source = "semantic search"

        elif mode == "keyword":
            docs = search_keyword_enhanced(question, company=company)
            if not docs:
                return "No relevant keyword documents found."
            context = "\n\n".join(docs)
            context_source = "keyword search"

        elif mode == "full":
            context = FULL_CONTEXT_FILE.read_text(encoding="utf-8")
            context_source = "full context file"

        else:
            return "\u274c Invalid mode."

        final_prompt = f"""
You are a competitive intelligence assistant specializing in cybersecurity vendors.

CRITICAL INSTRUCTIONS:
1. ONLY use information from the provided context below
2. Do NOT use general knowledge
3. If no answer, say: 'This info is not available.'
4. Cite sources like [source_name]
5. Be specific and factual

CONTEXT SOURCE: {context_source}

--- START OF CONTEXT ---
{context}
--- END OF CONTEXT ---

QUESTION: {question}

ANSWER:
"""
        return query_ollama(final_prompt)

    except Exception as e:
        traceback.print_exc()
        return f"\u274c Error: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--mode", default="semantic", choices=["semantic", "keyword", "full"])
    parser.add_argument("--source", default=None)
    parser.add_argument("--company", default=None)
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--slow", action="store_true")
    args = parser.parse_args()

    answer = ask_enhanced(
        question=args.question,
        mode=args.mode,
        source_filter=args.source,
        company=args.company,
        use_reranking=not args.no_rerank,
        n_results=4 if args.slow else 10,
        top_k=2 if args.slow else 5
    )
    print(f"\n\ud83d\udde3\ufe0f Answer:\n{answer}")
