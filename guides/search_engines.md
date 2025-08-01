# Search Engines

## KeywordSearchEngine

```python
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser
from whoosh.query import And, Term
from whoosh import index
import os

class KeywordSearchEngine:
    """Whoosh-based keyword search engine"""
    
    def __init__(self, index_dir: str = "keyword_index"):
        self.index_dir = index_dir
        self.schema = Schema(
            company=TEXT(stored=True),
            path=TEXT(stored=True),
            content=TEXT(stored=True)
        )
        self.ix = self._get_or_create_index()
    
    def _get_or_create_index(self):
        """Get existing index or create new one"""
        if index.exists_in(self.index_dir):
            return index.open_dir(self.index_dir)
        else:
            os.makedirs(self.index_dir, exist_ok=True)
            return index.create_in(self.index_dir, self.schema)
    
    def search(self, question: str, company_id: str = None, n_results: int = 5):
        """Search with optional company filtering"""
        try:
            with self.ix.searcher() as searcher:
                parser = QueryParser("content", self.ix.schema)
                content_query = parser.parse(question)
                
                # Add company filter if provided
                if company_id:
                    final_query = And([content_query, Term("company", company_id)])
                else:
                    final_query = content_query
                
                hits = searcher.search(final_query, limit=n_results)
                
                results = []
                for hit in hits:
                    results.append(SearchResult(
                        content=hit['content'],
                        path=hit['path'],
                        company=hit['company'],
                        score=hit.score,
                        source='keyword'
                    ))
                
                return results
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []
```

## SemanticSearchEngine

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticSearchEngine:
    """Semantic search engine using sentence transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self.documents = []
    
    def index_documents(self, documents: list):
        """Index documents for semantic search"""
        try:
            self.documents = documents
            texts = [doc['content'] for doc in documents]
            self.embeddings = self.model.encode(texts)
            print(f"Indexed {len(documents)} documents for semantic search")
        except Exception as e:
            print(f"Error indexing documents: {e}")
    
    def search(self, question: str, company_id: str = None, n_results: int = 5):
        """Semantic search with optional company filtering"""
        if self.embeddings is None:
            print("No embeddings available for semantic search")
            return []
        
        try:
            # Filter by company if specified
            filtered_docs = self.documents
            filtered_embeddings = self.embeddings
            
            if company_id:
                filtered_indices = [i for i, doc in enumerate(self.documents) 
                                  if doc.get('company') == company_id]
                filtered_docs = [self.documents[i] for i in filtered_indices]
                filtered_embeddings = self.embeddings[filtered_indices]
            
            if len(filtered_docs) == 0:
                return []
            
            # Encode query and compute similarities
            query_embedding = self.model.encode([question])
            similarities = np.dot(query_embedding, filtered_embeddings.T)[0]
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:n_results]
            
            results = []
            for idx in top_indices:
                doc = filtered_docs[idx]
                results.append(SearchResult(
                    content=doc['content'],
                    path=doc['path'],
                    company=doc.get('company', ''),
                    score=float(similarities[idx]),
                    source='semantic'
                ))
            
            return results
        except Exception as e:
            print(f"Semantic search error: {e}")
            return []
```

## Integration with Existing Code

### Replace Your Current Keyword Search

```python
# Your current function
def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    # Replace with:
    keyword_engine = KeywordSearchEngine("path/to/your/keyword_index")
    company_keystore = CompanyKeystore("path/to/your/company_index")
    
    # Normalize company name
    company_id = None
    if company:
        company_id = company_keystore.normalize_company_name(company)
    
    # Search
    results = keyword_engine.search(question, company_id, n_results)
    
    # Convert to your expected format if needed
    return [{"content": r.content, "path": r.path, "company": r.company} for r in results]
```

### Add Semantic Search to Existing System

```python
# Initialize once at startup
semantic_engine = SemanticSearchEngine()

# Load and index your documents
documents = []  # Your existing document loading logic
semantic_engine.index_documents(documents)

# Use semantic search
def search_semantic(question: str, company: str = None, n_results: int = 5):
    company_id = company_keystore.normalize_company_name(company) if company else None
    return semantic_engine.search(question, company_id, n_results)
```

## Key Benefits

1. **Drop-in Replacement**: Minimal changes to existing code
2. **Company Filtering**: Works with your existing company context
3. **Consistent Interface**: Same search signature across engines
4. **Error Handling**: Graceful degradation on failures
5. **Extensible**: Easy to add new search engines
