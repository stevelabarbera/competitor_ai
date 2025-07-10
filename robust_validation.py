# Add this validation layer to your search_engine.py and debug scripts

def safe_metadata_extract(metadatas, default_source="Unknown"):
    """Safely extract metadata, handling None values and missing keys"""
    sources = []
    issues = []
    
    for i, meta in enumerate(metadatas):
        if meta is None:
            sources.append("No Metadata")
            issues.append(f"Chunk {i}: None metadata")
        elif not isinstance(meta, dict):
            sources.append("Invalid Metadata")
            issues.append(f"Chunk {i}: metadata is {type(meta)}")
        else:
            source = meta.get('source', default_source)
            if not source or source.strip() == "":
                source = "Empty Source"
                issues.append(f"Chunk {i}: empty source field")
            sources.append(source)
    
    return sources, issues

def validate_collection_health(collection):
    """Run a health check on your ChromaDB collection"""
    print("🔍 Running collection health check...")
    
    # Get a sample of documents
    try:
        sample = collection.get(limit=100)  # Check first 100
        docs = sample.get('documents', [])
        metadatas = sample.get('metadatas', [])
        ids = sample.get('ids', [])
        
        print(f"📊 Sample size: {len(docs)} documents")
        
        # Check for None metadata
        none_meta_count = sum(1 for meta in metadatas if meta is None)
        print(f"❌ Documents with None metadata: {none_meta_count}")
        
        # Check for empty documents
        empty_docs = sum(1 for doc in docs if not doc or len(doc.strip()) < 10)
        print(f"📝 Empty/tiny documents: {empty_docs}")
        
        # Check for missing source fields
        missing_sources = 0
        for meta in metadatas:
            if meta and isinstance(meta, dict):
                if not meta.get('source'):
                    missing_sources += 1
        print(f"🏷️ Documents missing source field: {missing_sources}")
        
        # Sample some actual content
        print("\n📋 Sample documents:")
        for i in range(min(3, len(docs))):
            doc = docs[i]
            meta = metadatas[i]
            source = "None" if not meta else meta.get('source', 'Missing')
            print(f"  {i}: [{source}] {doc[:100]}...")
        
        return {
            'total_sample': len(docs),
            'none_metadata': none_meta_count,
            'empty_docs': empty_docs,
            'missing_sources': missing_sources
        }
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return None

# Also add this to your search functions for runtime validation
def search_semantic_safe(question: str, n_results: int = 5):
    """Semantic search with built-in validation"""
    try:
        results = collection.query(query_texts=[question], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        # Validate results before returning
        if not docs:
            print("⚠️ No documents returned from semantic search")
            return []
        
        # Check for metadata issues
        sources, issues = safe_metadata_extract(metadatas)
        if issues:
            print(f"⚠️ Found {len(issues)} metadata issues in search results")
            for issue in issues[:3]:  # Show first 3 issues
                print(f"  - {issue}")
        
        return docs
        
    except Exception as e:
        print(f"❌ Semantic search failed: {e}")
        return []

# Quick validation script you can run anytime
if __name__ == "__main__":
    from embedding_config import get_competitor_collection
    import chromadb
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = get_competitor_collection(client)
    
    health = validate_collection_health(collection)
    if health:
        total_issues = health['none_metadata'] + health['empty_docs'] + health['missing_sources']
        if total_issues == 0:
            print("✅ Collection looks healthy!")
        else:
            print(f"⚠️ Found {total_issues} potential issues - consider re-ingesting")
