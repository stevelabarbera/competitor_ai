def search_keyword_enhanced(question: str, company: str = None, company_matching: str = "exact", n_results: int = 5):
    """Enhanced search with company filtering
    
    Args:
        question: Search query
        company: Company name to filter by
        company_matching: "exact" or "fuzzy" matching mode
        n_results: Number of results to return
    """
    from whoosh.query import And, Term
    from whoosh.qparser import QueryParser
    
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        clean_question = question.replace("?", "").replace(",", " ")
        try:
            content_query = parser.parse(clean_question)
        except:
            content_query = parser.parse(f'"{clean_question}"')
        
        if company:
            if company_matching == "fuzzy":
                # Use company lookup index for fuzzy matching
                company_id = normalize_company_name(company)
                if not company_id:
                    print(f"⚠️ Company '{company}' not found in company index")
                    return []
                company_query = Term("company", company_id)
                print(f"🔍 Fuzzy match: '{company}' → '{company_id}'")
            else:
                # Simple exact matching
                company_query = Term("company", company)
                print(f"🔍 Exact match: '{company}'")
            
            final_query = And([content_query, company_query])
        else:
            final_query = content_query
        
        hits = searcher.search(final_query, limit=n_results)
        chunks = [hit["content"] for hit in hits]
        quality_filter = QualityFilter(min_words=50)
        quality_chunks = quality_filter.filter(chunks)
        
        return filter_chunk_quality(quality_chunks)

def ask_enhanced(question: str, mode: str = "semantic", source_filter: str = None, 
                company: str = None, company_matching: str = "exact", 
                use_reranking: bool = True, n_results: int = 10, top_k: int = 5) -> str:
    """Enhanced ask function with company matching options"""
    try:
        if mode == "semantic":
            docs = search_semantic_enhanced(question, n_results=n_results, source_filter=source_filter, use_reranking=use_reranking, top_k=top_k)
            if not docs:
                return "No relevant semantic documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "semantic search of your internal documents"

        elif mode == "keyword":
            docs = search_keyword_enhanced(question, company=company, company_matching=company_matching)
            if not docs:
                return "No relevant keyword documents found in your internal data."
            context = "\n\n".join(docs)
            context_source = "keyword search of your internal documents"

        elif mode == "hybrid":
            sem_docs = search_semantic_enhanced(question, n_results=n_results, source_filter=source_filter, use_reranking=use_reranking, top_k=top_k)
            key_docs = search_keyword_enhanced(question, company=company, company_matching=company_matching)
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
            print(f"🏢 Company filter: {company} ({company_matching} matching)")
        print(f"📊 Context preview: {context[:200]}...")
        return query_ollama(final_prompt)

    except Exception as e:
        return f"❌ Error during {mode} search: {e}"

# Updated CLI arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument("--mode", default="semantic", choices=["semantic", "keyword", "hybrid", "full"], help="Search mode")
    parser.add_argument("--source", default=None, help="Optional source filter")
    parser.add_argument("--company", default=None, help="Optional company filter")
    parser.add_argument("--company-matching", default="exact", choices=["exact", "fuzzy"], 
                       help="Company matching mode: exact (default) or fuzzy")
    parser.add_argument("--no-rerank", action="store_true", help="Disable LLM reranking")
    parser.add_argument("--slow", action="store_true", help="Use slow mode (lower RAM usage)")
    args = parser.parse_args()

    # Convert hyphenated argument to underscore for function parameter
    company_matching = args.company_matching

    answer = ask_enhanced(
        question=args.question,
        mode=args.mode,
        source_filter=args.source,
        company=args.company,
        company_matching=company_matching,
        use_reranking=not args.no_rerank,
        n_results=SEMANTIC_RESULTS_LIMIT,
        top_k=RERANK_TOP_K
    )
    print(f"\n💬 Answer:\n{answer}")

# Usage examples:
# python script.py --question "revenue" --company "Apple" --mode keyword
# python script.py --question "revenue" --company "Apple" --mode keyword --company-matching fuzzy
# python script.py --question "revenue" --company "AAPL" --mode hybrid --company-matching fuzzy