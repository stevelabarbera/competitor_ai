# ChromaDB Integration Guide

## Overview
This updated solution integrates your existing ChromaDB semantic search with Whoosh keyword search, leveraging your rich metadata structure and company extraction from paths.

## Key Adaptations for Your Setup

### 1. **ChromaDB Integration**
- Uses your existing `competitor_docs` collection
- Preserves your rich metadata structure
- Handles your path-based company extraction (`output/tenable_com/content.txt`)
- Maintains compatibility with your chunking strategy

### 2. **Metadata Preservation**
Your metadata structure is fully preserved:
```python
metadata = {
    "path": "output/tenable_com/content.txt",
    "file_size": 953976,
    "chunk_index": 138,
    "content_type": "pricing",
    "mentioned_companies": "...",
    "likely_boilerplate": True,
    "priority": 1,
    # ... all other fields
}
```

### 3. **Company Extraction**
Automatic company extraction from your path structure:
- `output/tenable_com/content.txt` → `Tenable`
- `output/microsoft_com/content.txt` → `Microsoft`
- Handles both underscore and domain patterns

## Integration Steps

### Step 1: Update Your Search Function

```python
# Replace your existing search function
def enhanced_search_with_chroma(question: str, company: str = None, 
                               content_type: str = None, search_type: str = "hybrid"):
    """Enhanced search using both ChromaDB and Whoosh"""
    
    # Initialize pipeline (do this once at startup)
    rag_pipeline = create_rag_pipeline({
        'chroma_collection': 'competitor_docs',
        'keyword_index_dir': 'keyword_index',
        'company_index_dir': 'company_index'
    })
    
    # Execute search
    results = rag_pipeline.search(
        question=question,
        company_input=company,
        content_type=content_type,
        search_type=search_type,
        n_results=5
    )
    
    return results
```

### Step 2: Setup Company Data from Your Paths

```python
def extract_companies_from_chroma():
    """Extract company list from your ChromaDB collection"""
    client = chromadb.HttpClient()
    collection = client.get_collection("competitor_docs")
    
    # Get all unique paths to extract companies
    results = collection.get(include=["metadatas"])
    
    companies = {}
    for metadata in results['metadatas']:
        path = metadata.get('path', '')
        if 'output/' in path:
            try:
                parts = path.split('/')
                if len(parts) >= 2 and parts[0] == 'output':
                    company_dir = parts[1]
                    company_name = company_dir.replace('_com', '').replace('_', ' ').title()
                    
                    if company_name not in companies:
                        companies[company_name] = {
                            'id': company_name.lower(),
                            'name': company_name,
                            'aliases': [company_name, company_dir],
                            'domain': company_dir.replace('_', '.') if '_com' in company_dir else '',
                            'document_count': 0,
                            'tags': []
                        }
                    
                    companies[company_name]['document_count'] += 1
            except Exception:
                continue
    
    return list(companies.values())

# Initialize company data
companies_data = extract_companies_from_chroma()
rag_pipeline.setup_company_data(companies_data)
```

### Step 3: Configure Search Types

```python
# Search configurations for different use cases
SEARCH_CONFIGS = {
    "vulnerability_research": {
        "search_type": "hybrid",
        "keyword_weight": 0.6,  # Higher for technical terms
        "semantic_weight": 0.4,
        "content_type": None
    },
    "pricing_analysis": {
        "search_type": "keyword",  # Exact matches for pricing
        "content_type": "pricing",
        "n_results": 10
    },
    "competitive_intelligence": {
        "search_type": "semantic",  # Conceptual understanding
        "semantic_weight": 0.7,
        "keyword_weight": 0.3,
        "n_results": 8
    },
    "boilerplate_excluded": {
        "search_type": "hybrid",
        "filter_boilerplate": True,
        "keyword_weight": 0.5,
        "semantic_weight": 0.5
    }
}

def search_with_config(question: str, config_name: str, company: str = None):
    """Search using predefined configuration"""
    config = SEARCH_CONFIGS.get(config_name, {})
    
    return rag_pipeline.search(
        question=question,
        company_input=company,
        search_type=config.get('search_type', 'hybrid'),
        content_type=config.get('content_type'),
        n_results=config.get('n_results', 5),
        keyword_weight=config.get('keyword_weight', 0.4),
        semantic_weight=config.get('semantic_weight', 0.6)
    )
```

## Advanced Features

### 1. **Content Type Filtering**
```python
# Search only pricing content
results = rag_pipeline.search(
    question="subscription pricing model",
    content_type="pricing",
    search_type="keyword"
)

# Search only general content
results = rag_pipeline.search(
    question="company overview",
    content_type="general",
    search_type="semantic"
)
```

### 2. **Boilerplate Handling**
```python
def filter_boilerplate_results(results: List[SearchResult]) -> List[SearchResult]:
    """Filter or down-rank boilerplate content"""
    filtered = []
    for result in results:
        if result.metadata.get('likely_boilerplate', False):
            # Reduce score for boilerplate
            result.score *= 0.3
        filtered.append(result)
    
    return sorted(filtered, key=lambda x: x.score, reverse=True)
```

### 3. **Company Mention Analysis**
```python
def analyze_company_mentions(results: List[SearchResult]) -> Dict:
    """Analyze mentioned companies in results"""
    company_mentions = {}
    
    for result in results:
        if result.mentioned_companies:
            mentions = result.mentioned_companies.split(',')
            for mention in mentions:
                mention = mention.strip()
                if mention:
                    company_mentions[mention] = company_mentions.get(mention, 0) + 1
    
    return dict(sorted(company_mentions.items(), key=lambda x: x[1], reverse=True))
```

### 4. **Multi-Company Comparison**
```python
def compare_companies(question: str, companies: List[str], search_type: str = "hybrid"):
    """Compare information across multiple companies"""
    comparison_results = {}
    
    for company in companies:
        results = rag_pipeline.search(
            question=question,
            company_input=company,
            search_type=search_type,
            n_results=3
        )
        
        comparison_results[company] = {
            'results': results['results'],
            'total_score': sum(r.score for r in results['results']),
            'content_types': list(set(r.content_type for r in results['results'] if r.content_type))
        }
    
    return comparison_results

# Example: Compare vulnerability approaches
comparison = compare_companies(
    question="vulnerability scanning approach",
    companies=["Tenable", "Rapid7", "Qualys"]
)
```

## Performance Optimizations

### 1. **Connection Pooling**
```python
class OptimizedRAGPipeline(EnhancedRAGPipeline):
    """Optimized version with connection pooling"""
    
    def __init__(