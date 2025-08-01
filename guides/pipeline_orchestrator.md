# Pipeline Orchestrator

## EnhancedRAGPipeline Class

```python
class EnhancedRAGPipeline:
    """Enhanced RAG pipeline combining keyword and semantic search"""
    
    def __init__(self, keyword_index_dir: str = "keyword_index", 
                 company_index_dir: str = "company_index"):
        self.company_keystore = CompanyKeystore(company_index_dir)
        self.keyword_engine = KeywordSearchEngine(keyword_index_dir)
        self.semantic_engine = SemanticSearchEngine()
        
    def search(self, question: str, company_input: str = None,
               search_type: str = "hybrid", n_results: int = 5,
               keyword_weight: float = 0.4, semantic_weight: float = 0.6):
        """
        Enhanced search combining keyword and semantic approaches
        
        Args:
            question: Search query
            company_input: Company name/alias to filter by
            search_type: 'keyword', 'semantic', or 'hybrid'
            n_results: Number of results to return
            keyword_weight: Weight for keyword search in hybrid mode
            semantic_weight: Weight for semantic search in hybrid mode
        """
        
        # Step 1: Normalize company input
        company_id = None
        company_info = None
        if company_input:
            company_id = self.company_keystore.normalize_company_name(company_input)
            if not company_id:
                return {
                    "error": f"Company '{company_input}' not found",
                    "results": [],
                    "search_type": search_type
                }
            company_info = self.company_keystore.find_company(company_input)
        
        # Step 2: Execute search based on type
        if search_type == "keyword":
            results = self.keyword_engine.search(question, company_id, n_results)
        elif search_type == "semantic":
            results = self.semantic_engine.search(question, company_id, n_results)
        elif search_type == "hybrid":
            results = self._hybrid_search(question, company_id, n_results, 
                                        keyword_weight, semantic_weight)
        else:
            return {"error": f"Unknown search type: {search_type}", "results": []}
        
        # Step 3: Enrich results with company information
        enriched_results = []
        for result in results:
            if not result.company_info and result.company:
                result.company_info = self.company_keystore.find_company(result.company)
            enriched_results.append(result)
        
        return {
            "results": enriched_results,
            "search_type": search_type,
            "company_filter": company_info,
            "total_results": len(enriched_results)
        }
    
    def _hybrid_search(self, question: str, company_id: str, 
                      n_results: int, keyword_weight: float, 
                      semantic_weight: float):
        """Combine keyword and semantic search results"""
        
        # Get results from both engines
        keyword_results = self.keyword_engine.search(question, company_id, n_results * 2)
        semantic_results = self.semantic_engine.search(question, company_id, n_results * 2)
        
        # Combine and rerank results
        combined_results = {}
        
        # Add keyword results
        for result in keyword_results:
            key = f"{result.path}:{result.content[:100]}"
            combined_results[key] = result
            combined_results[key].score *= keyword_weight
        
        # Add semantic results (merge if duplicate)
        for result in semantic_results:
            key = f"{result.path}:{result.content[:100]}"
            if key in combined_results:
                # Merge scores for duplicates
                combined_results[key].score += result.score * semantic_weight
                combined_results[key].source = "hybrid"
            else:
                result.score *= semantic_weight
                result.source = "semantic"
                combined_results[key] = result
        
        # Sort by combined score and return top results
        sorted_results = sorted(combined_results.values(), 
                              key=lambda x: x.score, reverse=True)
        
        return sorted_results[:n_results]
    
    def index_documents(self, documents: list):
        """Index documents for semantic search"""
        self.semantic_engine.index_documents(documents)
    
    def setup_company_data(self, companies_data: list):
        """Setup company keystore with data"""
        self.company_keystore.populate_from_data(companies_data)
```

## Simple Usage Wrapper

```python
def create_enhanced_search_function(keyword_index_dir, company_index_dir):
    """Create a simple search function for your existing code"""
    
    # Initialize once
    pipeline = EnhancedRAGPipeline(keyword_index_dir, company_index_dir)
    
    def enhanced_search(question: str, company: str = None, 
                       search_type: str = "hybrid", n_results: int = 5):
        """Drop-in replacement for your existing search"""
        result = pipeline.search(question, company, search_type, n_results)
        
        # Return just the results list if no errors
        if "error" not in result:
            return result["results"]
        else:
            print(f"Search error: {result['error']}")
            return []
    
    return enhanced_search, pipeline

# Usage
search_func, pipeline = create_enhanced_search_function(
    "path/to/keyword_index", 
    "path/to/company_index"
)

# Setup data once
pipeline.setup_company_data(your_companies_data)
pipeline.index_documents(your_documents)

# Use like your existing function
results = search_func("revenue growth", company="Apple", search_type="hybrid")
```

## Configuration Presets

```python
# Define search configurations for different use cases
SEARCH_CONFIGS = {
    "precise": {
        "search_type": "keyword",
        "n_results": 10,
        "description": "Exact term matching"
    },
    "exploratory": {
        "search_type": "semantic", 
        "n_results": 15,
        "description": "Conceptual understanding"
    },
    "balanced": {
        "search_type": "hybrid",
        "keyword_weight": 0.4,
        "semantic_weight": 0.6,
        "n_results": 10,
        "description": "Best of both worlds"
    }
}

def configured_search(question: str, company: str = None, 
                     config: str = "balanced", **kwargs):
    """Search with predefined configurations"""
    config_params = SEARCH_CONFIGS.get(config, SEARCH_CONFIGS["balanced"])
    config_params.update(kwargs)  # Allow override
    
    return pipeline.search(question, company, **config_params)
```

## Error Handling and Fallbacks

```python
def robust_search(question: str, company: str = None, search_type: str = "hybrid"):
    """Robust search with fallback strategies"""
    try:
        return pipeline.search(question, company, search_type)
    except Exception as e:
        print(f"Search failed: {e}")
        
        # Fallback to keyword search
        if search_type != "keyword":
            try:
                return pipeline.search(question, company, "keyword")
            except Exception as e2:
                print(f"Keyword fallback failed: {e2}")
        
        # Return empty results with error info
        return {
            "results": [],
            "error": str(e),
            "search_type": search_type,
            "fallback_attempted": True
        }
```

## Key Features

1. **Flexible Search Types**: Choose between keyword, semantic, or hybrid
2. **Company-Aware**: Leverages your existing company context
3. **Weighted Scoring**: Configurable weights for hybrid search
4. **Error Handling**: Graceful degradation and fallbacks
5. **Easy Integration**: Drop-in replacement for existing functions
6. **Extensible**: Easy to add new search types or configurations
