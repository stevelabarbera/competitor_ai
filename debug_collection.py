#!/usr/bin/env python3
"""
debug_collection.py - ChromaDB collection health checking and inspection utilities
"""

import chromadb
from pathlib import Path
from collections import Counter
from embedding_config import get_competitor_collection

# Configuration
ROOT_DIR = Path(__file__).resolve().parent
CHROMA_DB_PATH = ROOT_DIR / "chroma_db"

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

def validate_collection_health(collection, sample_size=20):  # Much smaller default
    """Run a lightweight health check on ChromaDB collection"""
    print("🔍 Running collection health check...")
    
    try:
        # Get collection info first - this should be fast
        print("📊 Getting collection count...")
        count = collection.count()
        print(f"📊 Total documents in collection: {count}")
        
        if count == 0:
            print("❌ Collection is empty!")
            return None
        
        # Use much smaller sample for memory-constrained systems
        sample_size = min(sample_size, count, 20)  # Cap at 20 documents
        print(f"🔬 Fetching small sample of {sample_size} documents...")
        sample = collection.get(limit=sample_size)
        docs = sample.get('documents', [])
        metadatas = sample.get('metadatas', [])
        ids = sample.get('ids', [])
        
        print(f"🔬 Analyzing sample of {len(docs)} documents...")
        
        # Health metrics
        none_meta_count = sum(1 for meta in metadatas if meta is None)
        empty_docs = sum(1 for doc in docs if not doc or len(doc.strip()) < 10)
        
        # Check document lengths
        doc_lengths = [len(doc.split()) for doc in docs if doc]
        if doc_lengths:
            min_length = min(doc_lengths)
            max_length = max(doc_lengths)
            avg_length = sum(doc_lengths) / len(doc_lengths)
            print(f"📏 Document lengths - Min: {min_length}, Max: {max_length}, Avg: {avg_length:.1f} words")
        
        # Source analysis
        sources, issues = safe_metadata_extract(metadatas)
        source_counts = Counter(sources)
        
        print(f"\n📋 Health Summary:")
        print(f"  ❌ Documents with None metadata: {none_meta_count}")
        print(f"  📝 Empty/tiny documents: {empty_docs}")
        print(f"  🏷️ Metadata issues found: {len(issues)}")
        
        print(f"\n📂 Source Distribution:")
        for source, count in source_counts.most_common(10):
            print(f"  {source}: {count}")
        
        # Show sample issues
        if issues:
            print(f"\n⚠️  Sample Issues:")
            for issue in issues[:5]:
                print(f"  - {issue}")
        
        # Show sample content
        print(f"\n📄 Sample Documents:")
        for i in range(min(3, len(docs))):
            doc = docs[i]
            meta = metadatas[i]
            source = "None" if not meta else meta.get('source', 'Missing')
            word_count = len(doc.split()) if doc else 0
            print(f"  [{source}] ({word_count} words): {doc[:150]}...")
        
        return {
            'total_docs': count,
            'sample_size': len(docs),
            'none_metadata': none_meta_count,
            'empty_docs': empty_docs,
            'metadata_issues': len(issues),
            'source_distribution': dict(source_counts),
            'doc_length_stats': {
                'min': min(doc_lengths) if doc_lengths else 0,
                'max': max(doc_lengths) if doc_lengths else 0,
                'avg': sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
            }
        }
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return None

def inspect_specific_source(collection, source_name, limit=10):
    """Inspect documents from a specific source"""
    print(f"🔍 Inspecting documents from source: {source_name}")
    
    try:
        results = collection.get(
            where={"source": source_name},
            limit=limit
        )
        
        docs = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        
        if not docs:
            print(f"❌ No documents found for source: {source_name}")
            return
        
        print(f"📊 Found {len(docs)} documents")
        
        for i, (doc, meta) in enumerate(zip(docs, metadatas)):
            word_count = len(doc.split()) if doc else 0
            print(f"\n📄 Document {i+1}:")
            print(f"  Metadata: {meta}")
            print(f"  Length: {word_count} words")
            print(f"  Content: {doc[:200]}...")
            
    except Exception as e:
        print(f"❌ Source inspection failed: {e}")

def find_duplicate_content(collection, sample_size=50):
    """Find potential duplicate content in the collection"""
    print("🔍 Scanning for duplicate content...")
    
    try:
        sample = collection.get(limit=sample_size)
        docs = sample.get('documents', [])
        
        # Simple duplicate detection based on first 100 characters
        content_fingerprints = {}
        duplicates = []
        
        for i, doc in enumerate(docs):
            if doc:
                fingerprint = doc[:100].strip()
                if fingerprint in content_fingerprints:
                    duplicates.append((i, content_fingerprints[fingerprint], fingerprint))
                else:
                    content_fingerprints[fingerprint] = i
        
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} potential duplicates:")
            for new_idx, orig_idx, fingerprint in duplicates[:5]:
                print(f"  Doc {new_idx} matches Doc {orig_idx}: {fingerprint[:50]}...")
        else:
            print("✅ No obvious duplicates found")
            
    except Exception as e:
        print(f"❌ Duplicate scan failed: {e}")

def test_search_quality(collection, test_queries=None):
    """Test search quality with sample queries"""
    if test_queries is None:
        test_queries = [
            "cybersecurity features",
            "pricing model",
            "threat detection",
            "competitive advantages"
        ]
    
    print("🧪 Testing search quality...")
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
            
            docs = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            
            if docs:
                for i, (doc, meta) in enumerate(zip(docs, metadatas)):
                    source = meta.get('source', 'Unknown') if meta else 'No metadata'
                    relevance_score = "High" if query.lower() in doc.lower() else "Low"
                    print(f"  {i+1}. [{source}] {relevance_score}: {doc[:100]}...")
            else:
                print("  ❌ No results found")
                
        except Exception as e:
            print(f"  ❌ Search failed: {e}")

if __name__ == "__main__":
    # Initialize ChromaDB client and collection
    print("🚀 Starting lightweight debug tool...")
    print("💾 Memory-optimized for 8GB systems")
    
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        print("✅ ChromaDB client initialized")
        
        collection = get_competitor_collection(client)
        print("✅ Collection loaded")
        
        print("=" * 60)
        print("🔧 ChromaDB Collection Debug Tool (Lightweight)")
        print("=" * 60)
        
        # Run health check with small sample
        health = validate_collection_health(collection, sample_size=10)
        
        if health and health['total_docs'] > 0:
            print("\n" + "=" * 40)
            print("🎯 QUICK ASSESSMENT")
            print("=" * 40)
            
            issues = health['none_metadata'] + health['empty_docs'] + health['metadata_issues']
            if issues == 0:
                print("✅ Sample looks healthy!")
            else:
                print(f"❌ Found {issues} issues in {health['sample_size']} documents")
                print("🔧 Consider running fixes and re-ingestion")
    
    except Exception as e:
        print(f"❌ Debug tool failed: {e}")
        print("💡 Try: Kill the process and run 'python debug_collection_mini.py'")
        
    print("\n💾 Debug complete - memory usage should be low now")