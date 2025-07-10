import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from embedding_config import get_competitor_collection
import subprocess
import json
from typing import List, Dict, Tuple

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
        return "llama3:instruct"  # fallback default

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

def llm_rerank_chunks(question: str, chunks: List[str], top_k: int = 5) -> List[str]:
    """Uses LLM to rerank chunks by relevance to the question."""
    if len(chunks) <= top_k:
        return chunks
    
    # Create a prompt for the LLM to rank chunks
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
        # Parse the response to get chunk indices
        indices = [int(x.strip()) for x in response.split(',') if x.strip().isdigit()]
        indices = [i for i in indices if 0 <= i < len(chunks)][:top_k]
        
        if not indices:
            return chunks[:top_k]
        
        return [chunks[i] for i in indices]
    except Exception as e:
        print(f"⚠️ Reranking failed: {e}, using original order")
        return chunks[:top_k]

def filter_chunk_quality(chunks: List[str], min_words: int = 50) -> List[str]:
    """Filter out low-quality chunks based on word count and content."""
    quality_chunks = []
    
    for chunk in chunks:
        words = chunk.split()
        if len(words) < min_words:
            continue
            
        # Skip chunks that are mostly boilerplate
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

def search_semantic_enhanced(question: str, n_results: int = 10, source_filter: str = None, use_reranking: bool = True):
    """Enhanced semantic search with filtering and reranking."""
    query_params = {
        "query_texts": [question],
        "n_results": n_results
    }
    
    # Add metadata filtering if specified
    if source_filter:
        query_params["where"] = {"source": source_filter}
    
    results = collection.query(**query_params)
    chunks = results.get("documents", [[]])[0]
    
    if not chunks:
        return []
    
    # Filter for quality
    quality_chunks = filter_chunk_quality(chunks)
    
    # Apply LLM reranking
    if use_reranking and quality_chunks:
        quality_chunks = llm_rerank_chunks(question, quality_chunks, top_k=5)
    
    return quality_chunks

def search_keyword_enhanced(question: str, n_results: int = 5):
    """Enhanced keyword search with better query parsing."""
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        
        # Clean the question for better keyword matching
        clean_question = question.replace("?", "").replace(",", " ")
        
        try:
            query = parser.parse(clean_question)
        except:
            # Fallback to simpler query
            query = parser.parse(f'"{clean_question}"')
        
        hits = searcher.search(query, limit=n_results)
        chunks = [hit["content"] for hit in hits]
        
        # Apply quality filtering
        return filter_chunk_quality(chunks)

def ask_enhanced(question: str, mode: str = "semantic", source_filter: str = None, use_reranking: bool = True) -> str:
    """Enhanced ask function with better context management."""
    try:
        if mode == "semantic":
            docs = search_semantic_enhanced(question, source_filter=source_filter, use_reranking=use_reranking)
            if not docs:
                return "No relevant semantic documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "semantic search of your internal documents"

        elif mode == "keyword":
            docs = search_keyword_enhanced(question)
            if not docs:
                return "No relevant keyword documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "keyword search of your internal documents"

        elif mode == "hybrid":
            sem_docs = search_semantic_enhanced(question, source_filter=source_filter, use_reranking=use_reranking)
            key_docs = search_keyword_enhanced(question)
            
            # Combine and deduplicate
            all_docs = []
            seen = set()
            for doc in sem_docs + key_docs:
                if doc and doc not in seen:
                    all_docs.append(doc)
                    seen.add(doc)
            
            if not all_docs:
                return "No relevant documents found from either search method in your internal data."
            
            # Limit total context and rerank if needed
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

        # Enhanced prompt with stronger instructions
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
        return f"❌ Error during {mode} search: {e}"

# Backward compatibility
def ask(question: str, mode: str = "semantic") -> str:
    """Backward compatible ask function."""
    return ask_enhanced(question, mode=mode)

# Debug function to inspect collection
def debug_collection_content(question: str = "cybersecurity", n_results: int = 5):
    """Debug function to inspect what's in your collection."""
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
    # Test the enhanced search
    test_question = "What are the key features of our competitors?"
    print("Testing enhanced search...")
    result = ask_enhanced(test_question, mode="semantic", use_reranking=True)
    print(f"Result: {result}")
