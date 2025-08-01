# Core Classes

## SearchResult Dataclass

```python
from dataclasses import dataclass
from typing import Dict, Optional

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
```

## CompanyKeystore Class

```python
from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC
from whoosh import index
import os

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
                from whoosh.qparser import MultifieldParser
                parser = MultifieldParser(["company_name", "aliases"], self.ix.schema)
                query = parser.parse(f'"{name_or_alias}"')
                results = searcher.search(query, limit=1)
                return dict(results[0]) if results else None
        except Exception as e:
            print(f"Error finding company {name_or_alias}: {e}")
            return None
    
    def normalize_company_name(self, user_input: str) -> Optional[str]:
        """Handle fuzzy company name matching"""
        if not user_input:
            return None
            
        # Try exact match first
        exact = self.find_company(user_input)
        if exact:
            return exact['company_id']
        
        # Try partial match
        try:
            with self.ix.searcher() as searcher:
                from whoosh.qparser import MultifieldParser
                parser = MultifieldParser(["company_name", "aliases"], self.ix.schema)
                query = parser.parse(f'*{user_input}*')
                results = searcher.search(query, limit=5)
                return results[0]['company_id'] if results else None
        except Exception as e:
            print(f"Error normalizing company name {user_input}: {e}")
            return None
    
    def populate_from_data(self, companies_data: list):
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
            print(f"Populated company index with {len(companies_data)} companies")
        except Exception as e:
            print(f"Error populating company index: {e}")
```

## Usage

```python
# Initialize
company_keystore = CompanyKeystore("path/to/company_index")

# Setup data
companies_data = [
    {
        "id": "apple",
        "name": "Apple Inc.",
        "aliases": ["Apple", "AAPL"],
        "industry": "Technology",
        "document_count": 150,
        "tags": ["tech", "public", "fortune500"]
    }
]
company_keystore.populate_from_data(companies_data)

# Use
company_id = company_keystore.normalize_company_name("Apple")
company_info = company_keystore.find_company("AAPL")
```

## Key Features

1. **Flexible Schema**: Easy to extend with more company metadata
2. **Alias Support**: Handles multiple names for same company
3. **Fuzzy Matching**: Partial name matching for user input
4. **Error Handling**: Graceful degradation on errors
5. **Easy Integration**: Drop-in replacement for your existing company logic
