#!/usr/bin/env python3
"""
ChromaDB Database Inspector - Quick script to see what's in your database
"""

import chromadb
import json
from embedding_config import get_competitor_collection
from datetime import datetime

def inspect_database(limit=10, show_content=True, show_metadata=True, filter_source=None):
    """Inspect the ChromaDB database contents."""
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = get_competitor_collection(client)
    
    print("🔍 CHROMADB INSPECTION REPORT")
    print("=" * 50)
    
    # Get collection info
    try:
        collection_count = collection.count()
        print(f"📊 Total documents in collection: {collection_count}")
    except Exception as e:
        print(f"❌ Error getting collection count: {e}")
        return
    
    if collection_count == 0:
        print("🚫 Database is empty!")
        return
    
    # Get sample documents
    try:
        print(f"\n📄 Retrieving sample documents (limit: {limit})...")
        
        # Get documents without any filters first
        results = collection.get(
            limit=limit,
            include=['documents', 'metadatas', 'ids']
        )
        
        print(f"✅ Retrieved {len(results['ids'])} documents")
        
        # Show overview statistics
        print(f"\n📈 OVERVIEW STATISTICS")
        print("-" * 30)
        
        # Analyze sources
        sources = {}
        content_types = {}
        directories = {}
        
        for metadata in results['metadatas']:
            if metadata:
                # Count sources
                source = metadata.get('source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
                
                # Count content types
                content_type = metadata.get('content_type', 'Unknown')
                content_types[content_type] = content_types.get(content_type, 0) + 1
                
                # Count directories
                directory = metadata.get('directory', 'Unknown')
                directories[directory] = directories.get(directory, 0) + 1
        
        print(f"📁 Sources: {len(sources)} unique files")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {source}: {count} chunks")
        
        print(f"\n📋 Content Types:")
        for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {ctype}: {count} chunks")
        
        print(f"\n📂 Directories:")
        for directory, count in sorted(directories.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {directory}: {count} chunks")
        
        # Show detailed document samples
        print(f"\n📋 DETAILED DOCUMENT SAMPLES")
        print("-" * 40)
        
        for i, (doc_id, document, metadata) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            print(f"\n--- Document {i+1} ---")
            print(f"🆔 ID: {doc_id}")
            
            if show_metadata and metadata:
                print(f"📊 Metadata:")
                for key, value in metadata.items():
                    if key in ['source', 'content_type', 'directory', 'chunk_index', 'word_count']:
                        print(f"  {key}: {value}")
                
                # Show additional metadata if available
                if 'mentioned_companies' in metadata:
                    print(f"  mentioned_companies: {metadata['mentioned_companies']}")
                if 'priority' in metadata:
                    print(f"  priority: {metadata['priority']}")
            
            if show_content and document:
                content_preview = document[:200] + "..." if len(document) > 200 else document
                print(f"📄 Content: {content_preview}")
                print(f"📏 Length: {len(document)} characters")
        
        # Filter by source if requested
        if filter_source:
            print(f"\n🔍 FILTERING BY SOURCE: {filter_source}")
            print("-" * 40)
            
            filtered_results = collection.get(
                where={"source": filter_source},
                limit=limit,
                include=['documents', 'metadatas', 'ids']
            )
            
            print(f"Found {len(filtered_results['ids'])} documents from {filter_source}")
            
            for i, (doc_id, document, metadata) in enumerate(zip(filtered_results['ids'], filtered_results['documents'], filtered_results['metadatas'])):
                if i < 3:  # Show first 3
                    print(f"\n{i+1}. {doc_id}")
                    print(f"   Content: {document[:150]}...")
    
    except Exception as e:
        print(f"❌ Error retrieving documents: {e}")
        import traceback
        traceback.print_exc()

def search_test(query, mode="semantic", limit=5):
    """Test search functionality."""
    print(f"\n🔍 SEARCH TEST: '{query}' (mode: {mode})")
    print("-" * 50)
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = get_competitor_collection(client)
    
    try:
        if mode == "semantic":
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            print(f"✅ Found {len(results['ids'][0])} results")
            
            for i, (doc_id, document, metadata, distance) in enumerate(zip(
                results['ids'][0], 
                results['documents'][0], 
                results['metadatas'][0],
                results['distances'][0]
            )):
                print(f"\n{i+1}. Score: {distance:.3f}")
                print(f"   ID: {doc_id}")
                if metadata:
                    print(f"   Source: {metadata.get('source', 'Unknown')}")
                    print(f"   Type: {metadata.get('content_type', 'Unknown')}")
                print(f"   Content: {document[:150]}...")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🚀 ChromaDB Database Inspector")
    print("=" * 50)
    
    # Basic inspection
    inspect_database(limit=10, show_content=True, show_metadata=True)
    
    # Test some searches
    test_queries = [
        "pricing information",
        "competitor analysis", 
        "security features",
        "CrowdStrike"
    ]
    
    print(f"\n🧪 SEARCH TESTS")
    print("=" * 30)
    
    for query in test_queries:
        try:
            search_test(query, mode="semantic", limit=3)
        except Exception as e:
            print(f"❌ Search test failed for '{query}': {e}")
    
    print(f"\n✅ Inspection complete!")

if __name__ == "__main__":
    main()