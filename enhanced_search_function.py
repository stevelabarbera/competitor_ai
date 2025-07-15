# Enhanced search function with company filtering

from whoosh.query import And, Term
from whoosh.qparser import QueryParser

def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    """Enhanced search with optional company filtering"""
    
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
        
        # Step 3: Execute searc
        hits = searcher.search(final_query, limit=n_results)
        
        # Step 4: Extract and filter (your existing logic)
        chunks = [hit["content"] for hit in hits]
        quality_filter = QualityFilter(min_words=50)
        quality_chunks = quality_filter.filter(chunks)
        
        return filter_chunk_quality(quality_chunks)

# Alternative: More robust company matching
def search_keyword_enhanced_v2(question: str, company: str = None, n_results: int = 5):
    """Enhanced search with fuzzy company matching"""
    
    with ix.searcher() as searcher:
        # Content query
        parser = QueryParser("content", ix.schema)
        clean_question = question.replace("?", "").replace(",", " ")
        try:
            content_query = parser.parse(clean_question)
        except:
            content_query = parser.parse(f'"{clean_question}"')
        
        # Company filter with fuzzy matching
        if company:
            # Try exact match first
            company_query = Term("company", company)
            final_query = And([content_query, company_query])
            hits = searcher.search(final_query, limit=n_results)
            
            # If no results, try partial match
            if not hits:
                company_parser = QueryParser("company", ix.schema)
                fuzzy_company = company_parser.parse(f"*{company}*")
                final_query = And([content_query, fuzzy_company])
                hits = searcher.search(final_query, limit=n_results)
        else:
            hits = searcher.search(content_query, limit=n_results)
        
        # Process results
        chunks = [hit["content"] for hit in hits]
        quality_filter = QualityFilter(min_words=50)
        quality_chunks = quality_filter.filter(chunks)
        
        return filter_chunk_quality(quality_chunks)

# Simple wrapper for backward compatibility
def search_keyword_enhanced_original(question: str, n_results: int = 5):
    """Original function signature for backward compatibility"""
    return search_keyword_enhanced(question, company=None, n_results=n_results)

# Usage examples:
# search_keyword_enhanced("what is the revenue?")  # All companies
search_keyword_enhanced("what is the revenue?", company="Apple")  # Apple only
# search_keyword_enhanced("what is the revenue?", company="AAPL")   # Should also work