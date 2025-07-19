import os
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from whoosh import index
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import And, Term, Or
from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC
from whoosh.analysis import StandardAnalyzer, KeywordAnalyzer
import numpy as np
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Unified search result structure"""
    content: str
    path: str
    company: str
    company_info: Optional[Dict] = None
    score: float = 0.0
    source: str = "unknown"  # 'keyword', 'semantic', 'hybrid'
    metadata: Dict = None

class CompanyKeystore:
    """Manages company metadata and normalization"""
    
    def __init__(self, index_dir: str = "company_index"):
        self.index_dir = index_dir
        self.schema = Schema(
            company_id=ID(stored=True, unique=True),
            company_name=TEXT(stored=True),
            aliases=KEYWORD(stored=True),
            industry=KEYWORD(stored=True),
            doc_count=NUMERIC(stored=True),
            tags=KEYWORD(stored=True)
        )
        self.ix = self._get_or_create_index()
    
    def _get_or_create_index(self):
        """Get existing index or create new one"""
        if index.exists_in(self.index_dir):
            return index.open_dir(self.index_dir)
        else:
            os.makedirs(self.index_dir, exist_ok=True)
            return index.create_in(self.index_dir, self.schema)
    
    def find_company(self, name_or_alias: str) -> Optional[Dict]:
        """Find company by name or alias"""
        try:
            with self.ix.searcher() as searcher:
                parser = MultifieldParser(["company_name", "aliases"], self.ix.schema)
                query = parser.parse(f'"{name_or_alias}"')
                results = searcher.search(query, limit=1)
                return dict(results[0]) if results else None
        except Exception as e:
            logger.error(f"Error finding company {name_or_alias}: {e}")
            return None
    
    def normalize_company_name(self, user_input: str) -> Optional[str]:
        """Handle fuzzy company name matching"""
        if not user_input:
            return None
            
        try:
            with self.ix.searcher() as searcher:
                # Try exact match first
                exact = self.find_company(user_input)
                if exact:
                    return exact['company_id']
                
                # Try partial match
                parser = MultifieldParser(["company_name", "aliases"], self.ix.schema)
                query = parser.parse(f'*{user_input}*')
                results = searcher.search(query, limit=5)
                
                return results[0]['company_id'] if results else None
        except Exception as e:
            logger.error(f"Error normalizing company name {user_input}: {e}")
            return None
    
    def populate_from_data(self, companies_data: List[Dict]):
        """Populate company index from data source"""
        try:
            writer = self.ix.writer()
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
            logger.info(f"Populated company index with {len(companies_data)} companies")
        except Exception as e:
            logger.error(f"Error populating company index: {e}")

class KeywordSearchEngine:
    """Whoosh-based keyword search engine"""
    
    def __init__(self, index_dir: str = "keyword_index"):
        self.index_dir = index_dir
        self.schema = Schema(
            company=TEXT(stored=True),
            path=TEXT(stored=True),
            content=TEXT(analyzer=StandardAnalyzer(), stored=True)
        )
        self.ix = self._get_or_create_index()
    
    def _get_or_create_index(self):
        """Get existing index or create new one"""
        if index.exists_in(self.index_dir):
            return index.open_dir(self.index_dir)
        else:
            os.makedirs(self.index_dir, exist_ok=True)
            return index.create_in(self.index_dir, self.schema)
    
    def search(self, question: str, company_id: Optional[str] = None, 
               n_results: int = 5) -> List[SearchResult]:
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
            logger.error(f"Keyword search error: {e}")
            return []

class SemanticSearchEngine:
    """Semantic search engine using sentence transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self.documents = []
    
    def index_documents(self, documents: List[Dict]):
        """Index documents for semantic search"""
        try:
            self.documents = documents
            texts = [doc['content'] for doc in documents]
            self.embeddings = self.model.encode(texts)
            logger.info(f"Indexed {len(documents)} documents for semantic search")
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
    
    def search(self, question: str, company_id: Optional[str] = None, 
               n_results: int = 5) -> List[SearchResult]:
        """Semantic search with optional company filtering"""
        if self.embeddings is None:
            logger.warning("No embeddings available for semantic search")
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
            logger.error(f"Semantic search error: {e}")
            return []

class EnhancedRAGPipeline:
    """Enhanced RAG pipeline combining keyword and semantic search"""
    
    def __init__(self, keyword_index_dir: str = "keyword_index", 
                 company_index_dir: str = "company_index"):
        self.company_keystore = CompanyKeystore(company_index_dir)
        self.keyword_engine = KeywordSearchEngine(keyword_index_dir)
        self.semantic_engine = SemanticSearchEngine()
        
    def search(self, question: str, company_input: Optional[str] = None,
               search_type: str = "hybrid", n_results: int = 5,
               keyword_weight: float = 0.4, semantic_weight: float = 0.6) -> Dict[str, Any]:
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
    
    def _hybrid_search(self, question: str, company_id: Optional[str], 
                      n_results: int, keyword_weight: float, 
                      semantic_weight: float) -> List[SearchResult]:
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
    
    def index_documents(self, documents: List[Dict]):
        """Index documents for semantic search"""
        self.semantic_engine.index_documents(documents)
    
    def setup_company_data(self, companies_data: List[Dict]):
        """Setup company keystore with data"""
        self.company_keystore.populate_from_data(companies_data)

# Example usage
if __name__ == "__main__":
    # Initialize the enhanced RAG pipeline
    rag_pipeline = EnhancedRAGPipeline()
    
    # Example company data
    companies_data = [
        {
            "id": "apple",
            "name": "Apple Inc.",
            "aliases": ["Apple", "AAPL"],
            "industry": "Technology",
            "document_count": 150,
            "tags": ["tech", "public", "fortune500"]
        },
        {
            "id": "google",
            "name": "Google LLC",
            "aliases": ["Google", "Alphabet", "GOOGL"],
            "industry": "Technology",
            "document_count": 200,
            "tags": ["tech", "public", "search"]
        }
    ]
    
    # Setup company data
    rag_pipeline.setup_company_data(companies_data)
    
    # Example documents for semantic search
    documents = [
        {
            "content": "Apple's iPhone sales increased by 15% in Q4 2024, driven by strong demand for the iPhone 15 Pro series.",
            "path": "/reports/apple_q4_2024.pdf",
            "company": "apple"
        },
        {
            "content": "Google's search advertising revenue grew 12% year-over-year, reaching $48.5 billion in the quarter.",
            "path": "/reports/google_q4_2024.pdf",
            "company": "google"
        }
    ]
    
    # Index documents
    rag_pipeline.index_documents(documents)
    
    # Example searches
    print("=== Keyword Search ===")
    results = rag_pipeline.search("iPhone sales", company_input="Apple", search_type="keyword")
    for result in results['results']:
        print(f"Score: {result.score:.3f} | Source: {result.source} | Company: {result.company}")
        print(f"Content: {result.content[:100]}...")
        print()
    
    print("=== Semantic Search ===")
    results = rag_pipeline.search("mobile phone revenue", company_input="Apple", search_type="semantic")
    for result in results['results']:
        print(f"Score: {result.score:.3f} | Source: {result.source} | Company: {result.company}")
        print(f"Content: {result.content[:100]}...")
        print()
    
    print("=== Hybrid Search ===")
    results = rag_pipeline.search("revenue growth", search_type="hybrid")
    for result in results['results']:
        print(f"Score: {result.score:.3f} | Source: {result.source} | Company: {result.company}")
        print(f"Content: {result.content[:100]}...")
        print()
