# Company Keystore Schema Options

from whoosh.fields import Schema, TEXT, ID, KEYWORD, DATETIME, NUMERIC
from whoosh.analysis import KeywordAnalyzer

# Option 1: Rich Company Profile Schema
company_schema = Schema(
    # Primary key
    company_id=ID(stored=True, unique=True),
    
    # Basic info
    company_name=TEXT(stored=True),
    company_aliases=KEYWORD(stored=True),  # "Apple,Apple Inc,AAPL"
    
    # Metadata
    industry=KEYWORD(stored=True),
    sector=KEYWORD(stored=True),
    headquarters=TEXT(stored=True),
    founded_year=NUMERIC(stored=True),
    
    # Document stats
    document_count=NUMERIC(stored=True),
    last_updated=DATETIME(stored=True),
    
    # Tags/categories
    tags=KEYWORD(stored=True),  # "tech,public,fortune500"
    
    # Search optimization
    searchable_text=TEXT(analyzer=KeywordAnalyzer(), stored=False)  # All text combined
)

# Option 2: Simple Lookup Schema (lighter)
simple_company_schema = Schema(
    company_id=ID(stored=True, unique=True),
    company_name=TEXT(stored=True),
    aliases=KEYWORD(stored=True),
    industry=KEYWORD(stored=True),
    doc_count=NUMERIC(stored=True),
    tags=KEYWORD(stored=True)
)

# Usage Examples:

# 1. Company lookup by name/alias
def find_company(name_or_alias):
    """Find company by name or alias"""
    with company_ix.searcher() as searcher:
        # Search both name and aliases
        query = f'company_name:"{name_or_alias}" OR aliases:"{name_or_alias}"'
        results = searcher.search(query, limit=1)
        return results[0] if results else None

# 2. Filter companies by industry
def get_companies_by_industry(industry):
    """Get all companies in specific industry"""
    with company_ix.searcher() as searcher:
        query = f'industry:"{industry}"'
        return list(searcher.search(query, limit=None))

# 3. Company enrichment for search results
def enrich_search_results(search_results):
    """Add company metadata to search results"""
    enriched = []
    for result in search_results:
        company_info = find_company(result['company'])
        enriched.append({
            'content': result['content'],
            'path': result['path'],
            'company_info': company_info
        })
    return enriched

# 4. Smart company matching
def normalize_company_name(user_input):
    """Handle fuzzy company name matching"""
    with company_ix.searcher() as searcher:
        # Try exact match first
        exact = find_company(user_input)
        if exact:
            return exact['company_id']
        
        # Try partial match
        query = f'company_name:*{user_input}* OR aliases:*{user_input}*'
        results = searcher.search(query, limit=5)
        
        # Return best match or None
        return results[0]['company_id'] if results else None

# Integration with main search
def search_with_company_filter(question, company_input=None, n_results=5):
    """Enhanced search with company metadata"""
    
    # Step 1: Normalize company input
    company_id = None
    if company_input:
        company_id = normalize_company_name(company_input)
        if not company_id:
            return {"error": f"Company '{company_input}' not found"}
    
    # Step 2: Search documents
    with main_ix.searcher() as searcher:
        parser = QueryParser("content", main_ix.schema)
        content_query = parser.parse(question)
        
        # Add company filter if provided
        if company_id:
            final_query = And([content_query, Term("company", company_id)])
        else:
            final_query = content_query
            
        hits = searcher.search(final_query, limit=n_results)
        
        # Step 3: Enrich results
        results = []
        for hit in hits:
            company_info = find_company(hit['company'])
            results.append({
                'content': hit['content'],
                'path': hit['path'],
                'company': company_info['company_name'] if company_info else hit['company'],
                'industry': company_info['industry'] if company_info else None,
                'score': hit.score
            })
    
    return results

# Best Practices for Company Keystore:

# 1. Index structure
"""
keyword_index/          # Main document index
company_index/          # Company metadata index
"""

# 2. Data population
def populate_company_index(companies_data):
    """Populate company index from data source"""
    writer = company_ix.writer()
    for company in companies_data:
        writer.add_document(
            company_id=company['id'],
            company_name=company['name'],
            aliases=','.join(company.get('aliases', [])),
            industry=company.get('industry', ''),
            doc_count=company.get('document_count', 0),
            tags=','.join(company.get('tags', []))
        )
    writer.commit()

# 3. Maintenance
def update_company_stats():
    """Update document counts and last_updated fields"""
    # Get document counts from main index
    # Update company index accordingly
    pass