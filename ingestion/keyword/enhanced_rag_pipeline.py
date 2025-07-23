import os
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from whoosh import index
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import And, Term, Or
from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC
from whoosh.analysis import StandardAnalyzer, KeywordAnalyzer
import chromadb
from chromadb.config import Settings
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Unified search result structure"""
    content: str
    path: str
    company: str
    metadata: Dict = None
    score: float = 0.0
    source: str = "unknown"  # 'keyword', 'semantic', 'hybrid'
    chunk_index: Optional[int] = None
    content_type: Optional[str] = None
    mentioned_companies: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

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
            tags=KEYWORD(stored=True),
            domain=TEXT(stored=True)  # Added for web scraped data
        )
        self.ix = self._get_or_create_index()
        self.company_mapping = {}  # Cache for quick lookups
    
    def _get_or_create_index(self):
        """Get existing index or create new one"""
        if index.exists_in(self.index_dir):
            return index.open_dir(self.index_dir)
        else:
            os.makedirs(self.index_dir, exist_ok=True)
            return index.create_in(self.index_dir, self.schema)
    
    def extract_company_from_path(self, path: str) -> Optional[str]:
        """Extract company from path like 'output/tenable_com/content.txt'"""
        try:
            parts = path.split('/')
            if len(parts) >= 2 and parts[0] == 'output':
                company_dir = parts[1]
                # Convert tenable_com to tenable
                company_name = company_dir.replace('_com', '').replace('_', ' ')
                return company_name.title()
        except Exception as e:
            logger.error(f"Error extracting company from path {path}: {e}")
        return None
    
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
            
        # Check cache first
        if user_input.lower() in self.company_mapping:
            return self.company_mapping[user_input.lower()]
            
        try:
            with self.ix.searcher() as searcher:
                # Try exact match first
                exact = self.find_company(user_input)
                if exact:
                    company_id = exact['company_id']
                    self.company_mapping[user_input.lower()] = company_id
                    return company_id
                
                # Try partial match
                parser = MultifieldParser(["company_name", "aliases"], self.ix.schema)
                query = parser.parse(f'*{user_input}*')
                results = searcher.search(query, limit=5)
                
                if results:
                    company_id = results[0]['company_id']
                    self.company_mapping[user_input.lower()] = company_id
                    return company_id
                    
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
                    tags=','.join(company.get('tags', [])),
                    domain=company.get('domain', '')
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
            content=TEXT(analyzer=StandardAnalyzer(), stored=True),
            chunk_index=NUMERIC(stored=True),
            content_type=KEYWORD(stored=True),
            mentioned_companies=TEXT(stored=True),
            priority=NUMERIC(stored=True)
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
               content_type: Optional[str] = None, n_results: int = 5) -> List[SearchResult]:
        """Search with optional company and content type filtering"""
        try:
            with self.ix.searcher() as searcher:
                parser = QueryParser("content", self.ix.schema)
                content_query = parser.parse(question)
                
                # Build compound query with filters
                queries = [content_query]
                
                if company_id:
                    queries.append(Term("company", company_id))
                
                if content_type:
                    queries.append(Term("content_type", content_type))
                
                final_query = And(queries) if len(queries) > 1 else content_query
                
                hits = searcher.search(final_query, limit=n_results)
                
                results = []
                for hit in hits:
                    results.append(SearchResult(
                        content=hit['content'],
                        path=hit['path'],
                        company=hit['company'],
                        score=hit.score,
                        source='keyword',
                        chunk_index=hit.get('chunk_index'),
                        content_type=hit.get('content_type'),
                        mentioned_companies=hit.get('mentioned_companies'),
                        metadata={
                            'priority': hit.get('priority', 0),
                            'search_type': 'keyword'
                        }
                    ))
                
                return results
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

class ChromaSemanticEngine:
    """ChromaDB-based semantic search engine"""
    
    def __init__(self, collection_name: str = "competitor_docs", 
                 chroma_host: str = "localhost", chroma_port: int = 8000):
        self.collection_name = collection_name
        #self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize or get existing collection"""
        try:

             # Connect to ChromaDB
            client = chromadb.Persistena.11cold, out, thereetClient(path="./chroma_db")
            collection = get_competitor_collection(client)
    
            self.collection = self.client.get_collection(self.collection_name)
            logger.info(f"✅ Found existing collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Collection {self.collection_name} not found: {e}")
            self.collection = None
    
    def search(self, question: str, company_filter: Optional[str] = None,
               content_type: Optional[str] = None, n_results: int = 5) -> List[SearchResult]:
        """Semantic search with optional filters"""
        if not self.collection:
            logger.warning("No collection available for semantic search")
            return []
        
        try:
            # Build where clause for filtering
            where_clause = {}
            if company_filter:
                # Filter by path containing company name
                where_clause["path"] = {"$contains": company_filter.lower()}
            
            if content_type:
                where_clause["content_type"] = content_type
            
            # Execute semantic search
            query_params = {
                "query_texts": [question],
                "n_results": n_results,
                "include": ["metadatas", "documents", "distances"]
            }
            
            if where_clause:
                query_params["where"] = where_clause
            
            results = self.collection.query(**query_params)
            
            # Convert ChromaDB results to SearchResult objects
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Extract company from path
                    company = self._extract_company_from_metadata(metadata)
                    
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 - distance if distance <= 1.0 else 0.0
                    
                    search_results.append(SearchResult(
                        content=doc,
                        path=metadata.get('path', ''),
                        company=company,
                        score=similarity_score,
                        source='semantic',
                        chunk_index=metadata.get('chunk_index'),
                        content_type=metadata.get('content_type'),
                        mentioned_companies=metadata.get('mentioned_companies'),
                        metadata={
                            'distance': distance,
                            'priority': metadata.get('priority', 0),
                            'file_size': metadata.get('file_size'),
                            'word_count': metadata.get('word_count'),
                            'likely_boilerplate': metadata.get('likely_boilerplate', False),
                            'search_type': 'semantic'
                        }
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
    
    def _extract_company_from_metadata(self, metadata: Dict) -> str:
        """Extract company name from metadata"""
        path = metadata.get('path', '')
        if 'output/' in path:
            try:
                parts = path.split('/')
                if len(parts) >= 2 and parts[0] == 'output':
                    company_dir = parts[1]
                    return company_dir.replace('_com', '').replace('_', ' ').title()
            except Exception:
                pass
        return metadata.get('company', 'Unknown')

class EnhancedRAGPipeline:
    """Enhanced RAG pipeline combining keyword and semantic search"""
    
    def __init__(self, keyword_index_dir: str = "keyword_index", 
                 company_index_dir: str = "company_index",
                 chroma_collection: str = "competitor_docs"):
        self.company_keystore = CompanyKeystore(company_index_dir)
        self.keyword_engine = KeywordSearchEngine(keyword_index_dir)
        self.semantic_engine = ChromaSemanticEngine(chroma_collection)
        
    def search(self, question: str, company_input: Optional[str] = None,
               content_type: Optional[str] = None, search_type: str = "hybrid", 
               n_results: int = 5, keyword_weight: float = 0.4, 
               semantic_weight: float = 0.6, rerank: bool = True) -> Dict[str, Any]:
        """
        Enhanced search combining keyword and semantic approaches
        
        Args:
            question: Search query
            company_input: Company name/alias to filter by
            content_type: Content type filter ('pricing', 'general', etc.)
            search_type: 'keyword', 'semantic', or 'hybrid'
            n_results: Number of results to return
            keyword_weight: Weight for keyword search in hybrid mode
            semantic_weight: Weight for semantic search in hybrid mode
            rerank: Whether to rerank results by combined score
        """
        
        # Step 1: Normalize company input
        company_id = None
        company_info = None
        if company_input:
            company_id = self.company_keystore.normalize_company_name(company_input)
            if not company_id:
                # Try to extract from path-like input
                if '_com' in company_input or '/' in company_input:
                    company_id = self.company_keystore.extract_company_from_path(company_input)
                
                if not company_id:
                    logger.warning(f"Company '{company_input}' not found, searching without filter")
            else:
                company_info = self.company_keystore.find_company(company_input)
        
        # Step 2: Execute search based on type
        if search_type == "keyword":
            results = self.keyword_engine.search(
                question, company_id, content_type, n_results
            )
        elif search_type == "semantic":
            results = self.semantic_engine.search(
                question, company_id, content_type, n_results
            )
        elif search_type == "hybrid":
            results = self._hybrid_search(
                question, company_id, content_type, n_results, 
                keyword_weight, semantic_weight, rerank
            )
        else:
            return {"error": f"Unknown search type: {search_type}", "results": []}
        
        # Step 3: Filter and enhance results
        filtered_results = self._filter_and_enhance_results(results, company_info)
        
        return {
            "results": filtered_results,
            "search_type": search_type,
            "company_filter": company_info,
            "content_type_filter": content_type,
            "total_results": len(filtered_results),
            "query": question
        }
    
    def _hybrid_search(self, question: str, company_id: Optional[str], 
                      content_type: Optional[str], n_results: int, 
                      keyword_weight: float, semantic_weight: float,
                      rerank: bool) -> List[SearchResult]:
        """Combine keyword and semantic search results"""
        
        # Get results from both engines with higher limit for better fusion
        search_limit = min(n_results * 3, 20)
        
        keyword_results = self.keyword_engine.search(
            question, company_id, content_type, search_limit
        )
        semantic_results = self.semantic_engine.search(
            question, company_id, content_type, search_limit
        )
        
        # Combine results using reciprocal rank fusion
        combined_results = {}
        
        # Add keyword results
        for rank, result in enumerate(keyword_results):
            key = f"{result.path}:{result.chunk_index}"
            if key in combined_results:
                combined_results[key].score += keyword_weight * (1.0 / (rank + 1))
            else:
                result.score = keyword_weight * (1.0 / (rank + 1))
                combined_results[key] = result
        
        # Add semantic results
        for rank, result in enumerate(semantic_results):
            key = f"{result.path}:{result.chunk_index}"
            if key in combined_results:
                combined_results[key].score += semantic_weight * (1.0 / (rank + 1))
                combined_results[key].source = "hybrid"
            else:
                result.score = semantic_weight * (1.0 / (rank + 1))
                result.source = "semantic"
                combined_results[key] = result
        
        # Sort by combined score and return top results
        sorted_results = sorted(combined_results.values(), 
                              key=lambda x: x.score, reverse=True)
        
        return sorted_results[:n_results]
    
    def _filter_and_enhance_results(self, results: List[SearchResult], 
                                   company_info: Optional[Dict]) -> List[SearchResult]:
        """Filter and enhance search results"""
        enhanced_results = []
        
        for result in results:
            # Skip likely boilerplate unless specifically requested
            if result.metadata and result.metadata.get('likely_boilerplate', False):
                # Lower the score for boilerplate content
                result.score *= 0.5
            
            # Enhance with company information
            if company_info and not result.metadata.get('company_info'):
                result.metadata['company_info'] = company_info
            
            # Extract more company context from mentioned_companies
            if result.mentioned_companies:
                result.metadata['extracted_companies'] = result.mentioned_companies
            
            enhanced_results.append(result)
        
        # Sort by score and return
        return sorted(enhanced_results, key=lambda x: x.score, reverse=True)
    
    def setup_company_data(self, companies_data: List[Dict]):
        """Setup company keystore with data"""
        self.company_keystore.populate_from_data(companies_data)
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the search collections"""
        stats = {
            "semantic_collection": None,
            "keyword_index": None,
            "company_index": None
        }
        
        try:
            if self.semantic_engine.collection:
                count = self.semantic_engine.collection.count()
                stats["semantic_collection"] = {"document_count": count}
        except Exception as e:
            stats["semantic_collection"] = {"error": str(e)}
        
        try:
            with self.keyword_engine.ix.searcher() as searcher:
                stats["keyword_index"] = {"document_count": searcher.doc_count()}
        except Exception as e:
            stats["keyword_index"] = {"error": str(e)}
        
        try:
            with self.company_keystore.ix.searcher() as searcher:
                stats["company_index"] = {"company_count": searcher.doc_count()}
        except Exception as e:
            stats["company_index"] = {"error": str(e)}
        
        return stats

# Example usage and integration helpers
def create_rag_pipeline(config: Dict = None) -> EnhancedRAGPipeline:
    """Factory function to create RAG pipeline with configuration"""
    if config is None:
        config = {}
    
    return EnhancedRAGPipeline(
        keyword_index_dir=config.get('keyword_index_dir', 'keyword_index'),
        company_index_dir=config.get('company_index_dir', 'company_index'),
        chroma_collection=config.get('chroma_collection', 'competitor_docs')
    )

def search_with_context(pipeline: EnhancedRAGPipeline, question: str, 
                       context: Dict = None) -> Dict[str, Any]:
    """Search with additional context parameters"""
    if context is None:
        context = {}
    
    return pipeline.search(
        question=question,
        company_input=context.get('company'),
        content_type=context.get('content_type'),
        search_type=context.get('search_type', 'hybrid'),
        n_results=context.get('n_results', 5),
        keyword_weight=context.get('keyword_weight', 0.4),
        semantic_weight=context.get('semantic_weight', 0.6)
    )

# Example usage
if __name__ == "__main__":
    # Initialize the enhanced RAG pipeline
    rag_pipeline = create_rag_pipeline()
    
    # Example company data matching your domain structure
    companies_data = [
        {
            "id": "tenable",
            "name": "Tenable Inc.",
            "aliases": ["Tenable", "Tenable.com"],
            "industry": "Cybersecurity",
            "domain": "tenable.com",
            "document_count": 285,
            "tags": ["security", "vulnerability", "public"]
        }
    ]
    
    # Setup company data
    rag_pipeline.setup_company_data(companies_data)
    #'''
    # Example searches
    print("=== Keyword Search ===")
    results = rag_pipeline.search(
        "vulnerability assessment", 
        company_input="tenable", 
        search_type="keyword"
    )
    for result in results['results']:
        print(f"Score: {result.score:.3f} | Source: {result.source}")
        print(f"Company: {result.company} | Type: {result.content_type}")
        print(f"Content: {result.content[:150]}...")
        print()
    #'''
    '''
    print("=== Semantic Search ===")
    results = rag_pipeline.search(
        "security scanning tools", 
        company_input="tenable", 
        search_type="semantic"
    )
    for result in results['results']:
        print(f"Score: {result.score:.3f} | Source: {result.source}")
        print(f"Company: {result.company} | Type: {result.content_type}")
        print(f"Content: {result.content[:150]}...")
        print()
    '''
    '''
    print("=== Hybrid Search ===")
    results = rag_pipeline.search(
        "GCP Cloud Run vulnerability", 
        search_type="hybrid",
        content_type="pricing"
    )
    for result in results['results']:
        print(f"Score: {result.score:.3f} | Source: {result.source}")
        print(f"Company: {result.company} | Type: {result.content_type}")
        print(f"Content: {result.content[:150]}...")
        print()
    '''
    # Get collection statistics
    stats = rag_pipeline.get_collection_stats()
    print(f"Collection Stats: {stats}")
