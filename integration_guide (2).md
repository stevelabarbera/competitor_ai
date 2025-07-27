# Integration Guide

## Quick Integration Steps

### Step 1: Install Dependencies

```bash
pip install sentence-transformers whoosh numpy
```

### Step 2: Create the Core Files

Create these files in your project:

```
your_project/
├── enhanced_rag/
│   ├── __init__.py
│   ├── core_classes.py      # CompanyKeystore, SearchResult
│   ├── search_engines.py    # KeywordSearchEngine, SemanticSearchEngine  
│   └── pipeline.py          # EnhancedRAGPipeline
```

### Step 3: Replace Your Existing Search Function

```python
# OLD: Your existing search_keyword_enhanced function
def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    # Your existing Whoosh logic
    pass

# NEW: Enhanced version
from enhanced_rag.pipeline import EnhancedRAGPipeline

# Initialize once at startup
rag_pipeline = EnhancedRAGPipeline(
    keyword_index_dir="path/to/your/keyword_index",
    company_index_dir="path/to/your/company_index"
)

def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    """Drop-in replacement with enhanced capabilities"""
    result = rag_pipeline.search(
        question=question,
        company_input=company,
        search_type="keyword",  # Keep existing behavior
        n_results=n_results
    )
    
    # Return in your expected format
    if "error" not in result:
        return [{"content": r.content, "path": r.path, "company": r.company} 
                for r in result["results"]]
    else:
        return []
```

### Step 4: Setup Your Data

```python
# Setup company data (run once)
companies_data = [
    {
        "id": "apple",
        "name": "Apple Inc.",
        "aliases": ["Apple", "AAPL"],
        "industry": "Technology",
        "document_count": 0,
        "tags": ["tech", "public"]
    },
    # ... more companies
]
rag_pipeline.setup_company_data(companies_data)

# Setup semantic search (run once)
documents = []  # Your existing document loading logic
rag_pipeline.index_documents(documents)
```

## Migration Strategy

### Phase 1: Minimal Integration (30 minutes)
1. Copy core classes into your project
2. Replace `search_keyword_enhanced` with enhanced version
3. Test with existing functionality

### Phase 2: Add Semantic Search (1 hour)
1. Load documents into semantic engine
2. Add new search endpoint for semantic search
3. Test semantic search functionality

### Phase 3: Enable Hybrid Search (1 hour)
1. Configure hybrid search weights
2. Add hybrid search endpoints
3. A/B test different search types

## Integration Patterns

### Pattern 1: Gradual Migration
```python
# Keep existing function, add new ones
def search_keyword_enhanced(question, company=None, n_results=5):
    # Your existing logic (unchanged)
    pass

def search_enhanced(question, company=None, search_type="hybrid", n_results=5):
    # New enhanced search
    return rag_pipeline.search(question, company, search_type, n_results)
```

### Pattern 2: Feature Flag
```python
USE_ENHANCED_SEARCH = False  # Feature flag

def search_keyword_enhanced(question, company=None, n_results=5):
    if USE_ENHANCED_SEARCH:
        return rag_pipeline.search(question, company, "keyword", n_results)
    else:
        # Your existing logic
        pass
```

### Pattern 3: Wrapper Function
```python
def create_search_wrapper(use_enhanced=True):
    if use_enhanced:
        return lambda q, c=None, n=5: rag_pipeline.search(q, c, "hybrid", n)
    else:
        return your_existing_search_function

# Use
search_func = create_search_wrapper(use_enhanced=True)
results = search_func("revenue growth", company="Apple")
```

## Data Migration

### Company Data Format
```python
# Your existing company data
existing_companies = [
    {"name": "Apple Inc.", "industry": "Tech"},
    {"name": "Google LLC", "industry": "Tech"},
]

# Convert to enhanced format
enhanced_companies = []
for i, company in enumerate(existing_companies):
    enhanced_companies.append({
        "id": f"company_{i}",  # Generate ID
        "name": company["name"],
        "aliases": [company["name"]],  # Start with name as alias
        "industry": company.get("industry", ""),
        "document_count": 0,
        "tags": []
    })
```

### Document Data Format
```python
# Your existing documents
existing_docs = [
    {"content": "...", "path": "...", "company": "Apple Inc."},
]

# Convert for semantic search
semantic_docs = []
for doc in existing_docs:
    # Map company name to company ID
    company_id = company_name_to_id.get(doc["company"], doc["company"])
    semantic_docs.append({
        "content": doc["content"],
        "path": doc["path"],
        "company": company_id
    })
```

## Testing Strategy

### Unit Tests
```python
def test_company_normalization():
    assert company_keystore.normalize_company_name("Apple") == "apple"
    assert company_keystore.normalize_company_name("AAPL") == "apple"

def test_keyword_search():
    results = keyword_engine.search("iPhone", "apple")
    assert len(results) > 0
    assert all(r.company == "apple" for r in results)

def test_semantic_search():
    results = semantic_engine.search("mobile phone", "apple")
    assert len(results) > 0
```

### Integration Tests
```python
def test_hybrid_search():
    results = rag_pipeline.search("revenue growth", "Apple", "hybrid")
    assert "results" in results
    assert len(results["results"]) > 0

def test_company_filtering():
    apple_results = rag_pipeline.search("revenue", "Apple")
    google_results = rag_pipeline.search("revenue", "Google")
    
    # Should return different companies
    assert apple_results["results"][0].company != google_results["results"][0].company
```

## Performance Considerations

### Initialization
```python
# Initialize once at startup, not per request
rag_pipeline = EnhancedRAGPipeline()

# Pre-load data
rag_pipeline.setup_company_data(companies_data)
rag_pipeline.index_documents(documents)
```

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_search(question, company=None, search_type="hybrid"):
    return rag_pipeline.search(question, company, search_type)
```

### Async Support
```python
import asyncio

async def async_search(question, company=None, search_type="hybrid"):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, rag_pipeline.search, question, company, search_type
    )
```

## Monitoring and Logging

```python
import logging
import time

def monitored_search(question, company=None, search_type="hybrid"):
    start_time = time.time()
    
    try:
        results = rag_pipeline.search(question, company, search_type)
        
        # Log successful search
        logging.info(f"Search completed: {search_type}, {len(results.get('results', []))} results, {time.time() - start_time:.
