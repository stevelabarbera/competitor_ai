# Enhanced RAG Pipeline Integration Guide

## Overview
This solution integrates your Whoosh keyword store with semantic search to create a unified, company-aware RAG pipeline that provides more accurate and contextually relevant results.

## Key Features

### 1. **Company-Aware Search**
- Normalizes company names and aliases
- Filters results by company context
- Enriches results with company metadata

### 2. **Multi-Modal Search**
- **Keyword Search**: Exact term matching via Whoosh
- **Semantic Search**: Contextual understanding via sentence transformers
- **Hybrid Search**: Combines both approaches with weighted scoring

### 3. **Enhanced Accuracy**
- Leverages company context to improve relevance
- Combines complementary search methods
- Provides unified scoring and ranking

## Integration Steps

### Step 1: Replace Existing Search Functions

```python
# Replace your current search_keyword_enhanced function
def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    """Legacy wrapper for backward compatibility"""
    return rag_pipeline.search(
        question=question,
        company_input=company,
        search_type="keyword",
        n_results=n_results
    )

# New enhanced search function
def enhanced_search(question: str, company: str = None, search_type: str = "hybrid", 
                   n_results: int = 5, **kwargs):
    """Enhanced search with multiple modes"""
    return rag_pipeline.search(
        question=question,
        company_input=company,
        search_type=search_type,
        n_results=n_results,
        **kwargs
    )
```

### Step 2: Initialize the Pipeline

```python
# Initialize once at startup
rag_pipeline = EnhancedRAGPipeline(
    keyword_index_dir="path/to/your/keyword_index",
    company_index_dir="path/to/your/company_index"
)

# Load your company data
companies_data = load_company_data()  # Your existing function
rag_pipeline.setup_company_data(companies_data)

# Index documents for semantic search
documents = load_documents_from_directories()  # Your existing function
rag_pipeline.index_documents(documents)
```

### Step 3: Update Your Document Indexing

```python
# Add to your build_woosh_index.py
def build_enhanced_index():
    """Build both keyword and semantic indexes"""
    
    # Build keyword index (existing logic)
    documents = collect_documents_from_directory()
    build_keyword_index(documents)
    
    # Build semantic index (new)
    rag_pipeline.index_documents(documents)
    
    # Update company statistics
    update_company_document_counts()
```

## Configuration Options

### Search Type Configuration

```python
# Configuration for different use cases
SEARCH_CONFIGS = {
    "precise": {
        "search_type": "keyword",
        "n_results": 10
    },
    "exploratory": {
        "search_type": "semantic", 
        "n_results": 15
    },
    "balanced": {
        "search_type": "hybrid",
        "keyword_weight": 0.4,
        "semantic_weight": 0.6,
        "n_results": 10
    },
    "company_focused": {
        "search_type": "hybrid",
        "keyword_weight": 0.6,  # Higher weight for exact matches
        "semantic_weight": 0.4,
        "n_results": 8
    }
}
```

### Company Data Structure

```python
# Expected company data format
company_data_example = {
    "id": "unique_company_id",
    "name": "Official Company Name",
    "aliases": ["Common Name", "Stock Symbol", "Abbreviation"],
    "industry": "Industry Category",
    "document_count": 0,  # Will be updated automatically
    "tags": ["tag1", "tag2", "tag3"]
}
```

## Performance Optimizations

### 1. **Caching Strategy**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_search(question: str, company: str = None, search_type: str = "hybrid"):
    """Cache frequent searches"""
    return rag_pipeline.search(question, company, search_type)
```

### 2. **Batch Processing**
```python
def batch_search(questions: List[str], company: str = None) -> List[Dict]:
    """Process multiple queries efficiently"""
    results = []
    for question in questions:
        result = rag_pipeline.search(question, company)
        results.append(result)
    return results
```

### 3. **Incremental Updates**
```python
def update_document_index(new_documents: List[Dict]):
    """Incrementally update indexes"""
    # Update keyword index
    with keyword_engine.ix.writer() as writer:
        for doc in new_documents:
            writer.add_document(**doc)
    
    # Update semantic index
    all_documents = load_all_documents()
    rag_pipeline.index_documents(all_documents)
```

## Usage Examples

### Basic Company-Filtered Search
```python
# Search within a specific company
results = rag_pipeline.search(
    question="quarterly revenue growth",
    company_input="Apple",
    search_type="hybrid"
)

for result in results['results']:
    print(f"Company: {result.company}")
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.content[:200]}...")
```

### Multi-Company Comparison
```python
# Compare across companies
companies = ["Apple", "Google", "Microsoft"]
comparison_results = {}

for company in companies:
    results = rag_pipeline.search(
        question="AI strategy and investments",
        company_input=company,
        search_type="hybrid",
        n_results=5
    )
    comparison_results[company] = results
```

### Adaptive Search Strategy
```python
def adaptive_search(question: str, company: str = None):
    """Adapt search strategy based on query characteristics"""
    
    # Use keyword search for specific terms
    if any(term in question.lower() for term in ["price", "date", "number", "when"]):
        return rag_pipeline.search(question, company, "keyword")
    
    # Use semantic search for conceptual queries
    elif any(term in question.lower() for term in ["similar", "related", "like", "about"]):
        return rag_pipeline.search(question, company, "semantic")
    
    # Default to hybrid
    else:
        return rag_pipeline.search(question, company, "hybrid")
```

## Monitoring and Analytics

### Search Performance Metrics
```python
def track_search_performance(question: str, company: str, search_type: str):
    """Track search performance metrics"""
    start_time = time.time()
    results = rag_pipeline.search(question, company, search_type)
    end_time = time.time()
    
    metrics = {
        "query": question,
        "company": company,
        "search_type": search_type,
        "result_count": len(results['results']),
        "response_time": end_time - start_time,
        "timestamp": datetime.now()
    }
    
    # Log or store metrics
    log_search_metrics(metrics)
    return results
```

## Error Handling and Fallbacks

```python
def robust_search(question: str, company: str = None, search_type: str = "hybrid"):
    """Robust search with fallback strategies"""
    try:
        return rag_pipeline.search(question, company, search_type)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        
        # Fallback to keyword search
        if search_type != "keyword":
            try:
                return rag_pipeline.search(question, company, "keyword")
            except Exception as e2:
                logger.error(f"Keyword fallback failed: {e2}")
        
        # Return empty results with error info
        return {
            "results": [],
            "error": str(e),
            "search_type": search_type,
            "fallback_attempted": True
        }
```

## Migration Checklist

- [ ] Install required dependencies (`sentence-transformers`, `whoosh`, `numpy`)
- [ ] Update your existing `build_woosh_index.py` to use the new structure
- [ ] Migrate company data to the new schema
- [ ] Test keyword search compatibility
- [ ] Build semantic embeddings for existing documents
- [ ] Update search endpoints to use new pipeline
- [ ] Add monitoring and logging
- [ ] Performance test with production data
- [ ] Update documentation and API specs

## Benefits of This Integration

1. **Improved Accuracy**: Company context reduces false positives
2. **Better Recall**: Semantic search finds relevant content with different wording
3. **Flexibility**: Choose search strategy based on use case
4. **Scalability**: Efficient indexing and caching strategies
5. **Maintainability**: Clean separation of concerns and modular design

This integration maintains backward compatibility while adding powerful new capabilities to your RAG pipeline.
