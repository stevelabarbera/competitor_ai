import os
import argparse
from pathlib import Path
import chromadb
from chromadb.config import Settings
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from embedding_config import get_competitor_collection
import subprocess
import json
import traceback
from typing import List, Dict, Tuple
from chunk_filtering.quality_filter import QualityFilter

ROOT_DIR = Path(__file__).resolve().parent
CHROMA_DB_PATH = ROOT_DIR / "chroma_db"
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
FULL_CONTEXT_FILE = ROOT_DIR / "full_context.txt"
MODEL_CONFIG_FILE = ROOT_DIR / "config_model.txt"

def get_model_name():
    try:
        return MODEL_CONFIG_FILE.read_text().strip()
    except Exception as e:
        print(f"⚠️ Could not read model config file: {e}")
        return "llama3:instruct"

client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
collection = get_competitor_collection(client)
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
'''
def llm_rerank_chunks(question: str, chunks: List[str], top_k: int = 5) -> List[str]:
    if len(chunks) <= top_k:
        return chunks

    chunk_list = "\n".join([f"[{i}] {chunk[:200]}..." for i, chunk in enumerate(chunks)])
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
        if not indices:
            return chunks[:top_k]
        return [chunks[i] for i in indices]
    except Exception as e:
        print(f"⚠️ Reranking failed: {e}, using original order")
        return chunks[:top_k]
'''
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
        if not indices:
            return chunks[:top_k]
        return [chunks[i] for i in indices]
    except Exception as e:
        print(f"⚠️ Reranking failed: {e}, using original order")
        return chunks[:top_k]

def filter_chunk_quality(chunks: List[str], min_words: int = 50) -> List[str]:
    quality_chunks = []
    for chunk in chunks:
        words = chunk.split()
        if len(words) < min_words:
            continue
        chunk_lower = chunk.lower()
        boilerplate_signals = [
            "terms and conditions", "privacy policy", "copyright",
            "all rights reserved", "disclaimer", "agreement",
            "legal notice", "cookie policy"
        ]
        if any(signal in chunk_lower for signal in boilerplate_signals):
            continue
        quality_chunks.append(chunk)
    return quality_chunks

def search_semantic_enhanced(question: str, n_results: int = 10, source_filter: str = None, use_reranking: bool = True, top_k: int = 5):
    query_params = {
        "query_texts": [question],
        "n_results": n_results
    }
    if source_filter:
        query_params["where"] = {"source": source_filter}

    results = collection.query(**query_params)
    print("📦 Raw Chroma query result:", json.dumps(results, indent=2, default=str))

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents or not metadatas:
        return []

    chunk_meta_pairs = list(zip(documents, metadatas))

    # Apply quality filter
    quality_filter = QualityFilter(min_words=50)
    filtered_pairs = []
    for chunk, meta in chunk_meta_pairs:
        if chunk.strip() and len(chunk.split()) >= quality_filter.min_words:
            if not any(signal in chunk.lower() for signal in quality_filter.boilerplate_signals):
                cleaned = "\n".join(line.strip() for line in chunk.splitlines() if line.strip())
                filtered_pairs.append((cleaned, meta))

    if not filtered_pairs:
        return []

    # Rerank
    if use_reranking:
        filtered_pairs = llm_rerank_chunks(question, filtered_pairs, top_k=top_k)

    return filtered_pairs

def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    """Enhanced search with optional company filtering"""
    from whoosh.query import And, Term
    from whoosh.qparser import QueryParser
    from chunk_filtering.quality_filter import QualityFilter
    
    with ix.searcher() as searcher:
        # Step 1: Parse content query (your existing logic)
        parser = QueryParser("content", ix.schema)
        clean_question = question.replace("?", "").replace(",", " ")
        try:
            content_query = parser.parse(clean_question)
        except:
            content_query = parser.parse(f'"{clean_question}"')
        
        # Step 2: Add company filter if provided
        if company:
            company_query = Term("company", company)
            final_query = And([content_query, company_query])
        else:
            final_query = content_query
        
        # Step 3: Execute search
        hits = searcher.search(final_query, limit=n_results)
        
        # Step 4: Extract and filter (your existing logic)
        chunks = [hit["content"] for hit in hits]
        quality_filter = QualityFilter(min_words=50)
        quality_chunks = quality_filter.filter(chunks)
        
        return filter_chunk_quality(quality_chunks)

# Update your ask_enhanced function to pass company parameter
def ask_enhanced(question: str, mode: str = "semantic", source_filter: str = None, 
                company: str = None, use_reranking: bool = True, n_results: int = 10, 
                top_k: int = 5) -> str:
    try:
        if mode == "semantic":
            docs = search_semantic_enhanced(question, n_results=n_results, source_filter=source_filter, use_reranking=use_reranking, top_k=top_k)
            if not docs:
                return "No relevant semantic documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "semantic search of your internal documents"

        elif mode == "keyword":
            docs = search_keyword_enhanced(question, company=company)  # Added company parameter
            if not docs:
                return "No relevant keyword documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "keyword search of your internal documents"

        elif mode == "hybrid":
            sem_docs = search_semantic_enhanced(question, n_results=n_results, source_filter=source_filter, use_reranking=use_reranking, top_k=top_k)
            key_docs = search_keyword_enhanced(question, company=company)  # Added company parameter
            all_docs = []
            seen = set()
            for doc in sem_docs + key_docs:
                if doc and doc not in seen:
                    all_docs.append(doc)
                    seen.add(doc)
            if not all_docs:
                return "No relevant documents found from either search method in your internal data."
            if len(all_docs) > 7:
                all_docs = llm_rerank_chunks(question, all_docs, top_k=7)
            context = "\n\n".join(all_docs)
            context_source = "hybrid search of your internal documents"

        elif mode == "full":
            try:
                context = FULL_CONTEXT_FILE.read_text(encoding="utf-8")
                context_source = "full context file"
            except Exception as e:
                return f"❌ Failed to load full context: {e}"
        else:
            return "❌ Invalid mode selected."

        final_prompt = f"""
You are a competitive intelligence assistant specializing in cybersecurity vendors. You have access to internal company documents and competitor analysis.

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
        print(f"🔍 Using {mode} mode with {len(context)} characters of context")
        if company:
            print(f"🏢 Filtering by company: {company}")
        print(f"📊 Context preview: {context[:200]}...")
        return query_ollama(final_prompt)

    except Exception as e:
        print("💥 Full traceback:")
        traceback.print_exc()
        return f"❌ Error during {mode} search: {e}"

# Usage examples:
# python script.py --question "What is their revenue?" --mode keyword --company "Apple"
# python script.py --question "pricing strategy" --mode hybrid --company "Microsoft"

'''
def search_keyword_enhanced(question: str, n_results: int = 5):
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        clean_question = question.replace("?", "").replace(",", " ")
        try:
            query = parser.parse(clean_question)
        except:
            query = parser.parse(f'"{clean_question}"')
        hits = searcher.search(query, limit=n_results)
        chunks = [hit["content"] for hit in hits]
        quality_filter = QualityFilter(min_words=50)
        quality_chunks = quality_filter.filter(chunks)

        return filter_chunk_quality(quality_chunks)
'''
def ask_enhanced(question: str, mode: str = "semantic", source_filter: str = None, use_reranking: bool = True, n_results: int = 10, top_k: int = 5) -> str:
    try:
        if mode == "semantic":
            docs = search_semantic_enhanced(question, n_results=n_results, source_filter=source_filter, use_reranking=use_reranking, top_k=top_k)
            if not docs:
                return "No relevant semantic documents found in your internal data."
            context = "\n\n".join( f"[Company: {meta.get('mentioned_companies', 'Unknown')}]\n{chunk}"
                for chunk, meta in docs
            )
            context_source = "semantic search of your internal documents"

        elif mode == "keyword":
            docs = search_keyword_enhanced(question)
            if not docs:
                return "No relevant keyword documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "keyword search of your internal documents"

        elif mode == "hybrid":
            sem_docs = search_semantic_enhanced(question, n_results=n_results, source_filter=source_filter, use_reranking=use_reranking, top_k=top_k)
            key_docs = search_keyword_enhanced(question)
            all_docs = []
            seen = set()
            for doc in sem_docs + key_docs:
                if doc and doc not in seen:
                    all_docs.append(doc)
                    seen.add(doc)
            if not all_docs:
                return "No relevant documents found from either search method in your internal data."
            if len(all_docs) > 7:
                all_docs = llm_rerank_chunks(question, all_docs, top_k=7)
            context = "\n\n".join(all_docs)
            context_source = "hybrid search of your internal documents"

        elif mode == "full":
            try:
                context = FULL_CONTEXT_FILE.read_text(encoding="utf-8")
                context_source = "full context file"
            except Exception as e:
                return f"❌ Failed to load full context: {e}"
        else:
            return "❌ Invalid mode selected."

        final_prompt = f"""
You are a competitive intelligence assistant specializing in cybersecurity vendors. You have access to internal company documents and competitor analysis.

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
        print(f"🔍 Using {mode} mode with {len(context)} characters of context")
        print(f"📊 Context preview: {context[:200]}...")
        return query_ollama(final_prompt)

    except Exception as e:
        print("💥 Full traceback:")
        traceback.print_exc()
        return f"❌ Error during {mode} search: {e}"

def ask(question: str, mode: str = "semantic") -> str:
    return ask_enhanced(question, mode=mode)

def debug_collection_content(question: str = "cybersecurity", n_results: int = 5):
    results = collection.query(query_texts=[question], n_results=n_results)
    print("🔍 DEBUG: Collection Contents")
    print(f"Query: {question}")
    print(f"Results found: {len(results.get('documents', [[]])[0])}")
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    for i, (doc, meta) in enumerate(zip(docs, metadatas)):
        print(f"\n--- Result {i+1} ---")
        print(f"Source: {meta.get('source', 'Unknown')}")
        print(f"Content preview: {doc[:200]}...")
        print(f"Word count: {len(doc.split())}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument("--mode", default="semantic", choices=["semantic", "keyword", "hybrid", "full"], help="Search mode")
    parser.add_argument("--source", default=None, help="Optional source filter")
    parser.add_argument("--no-rerank", action="store_true", help="Disable LLM reranking")
    parser.add_argument("--slow", action="store_true", help="Use slow mode (lower RAM usage)")
    args = parser.parse_args()

    SLOW_MODE = args.slow
    SEMANTIC_RESULTS_LIMIT = 4 if SLOW_MODE else 10
    RERANK_TOP_K = 2 if SLOW_MODE else 5

    print(f"🔧 Using embedding model: {get_model_name()}")
    print(f"Using slow mode: {SLOW_MODE},  RERANK_TOP_K:{RERANK_TOP_K}")
    print("✅ Found existing collection: competitor_docs")

    answer = ask_enhanced(
        question=args.question,
        mode=args.mode,
        source_filter=args.source,
        use_reranking=not args.no_rerank,
        n_results=SEMANTIC_RESULTS_LIMIT,
        top_k=RERANK_TOP_K
    )
    print(f"\n💬 Answer:\n{answer}")
