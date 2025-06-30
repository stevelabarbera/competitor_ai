#!/usr/bin/env python3
"""
Collection Debug and Quality Analysis Tool

This script helps you understand what's in your ChromaDB collection
and identify potential quality issues with your chunks.
"""

import chromadb
from embedding_config import get_competitor_collection
import argparse
from collections import Counter
import re

def analyze_chunk_quality(chunks, metadatas):
    """Analyze the quality of chunks in the collection."""
    print("\n" + "="*50)
    print("📊 CHUNK QUALITY ANALYSIS")
    print("="*50)
    
    # Basic statistics
    word_counts = [len(chunk.split()) for chunk in chunks]
    char_counts = [len(chunk) for chunk in chunks]
    
    print(f"Total chunks analyzed: {len(chunks)}")
    print(f"Average words per chunk: {sum(word_counts) / len(word_counts):.1f}")
    print(f"Average characters per chunk: {sum(char_counts) / len(char_counts):.1f}")
    print(f"Shortest chunk: {min(word_counts)} words")
    print(f"Longest chunk: {max(word_counts)} words")
    
    # Source distribution
    sources = [meta.get('source', 'Unknown') for meta in metadatas]
    source_counts = Counter(sources)
    
    print(f"\n📁 SOURCE DISTRIBUTION:")
    for source, count in source_counts.most_common(10):
        print(f"  {source}: {count} chunks")
    
    # Quality issues detection
    print(f"\n⚠️  POTENTIAL QUALITY ISSUES:")
    
    # Very short chunks
    short_chunks = [i for i, wc in enumerate(word_counts) if wc < 30]
    print(f"  Very short chunks (< 30 words): {len(short_chunks)}")
    
    # Very long chunks
    long_chunks = [i for i, wc in enumerate(word_counts) if wc > 800]
    print(f"  Very long chunks (> 800 words): {len(long_chunks)}")
    
    # Boilerplate detection
    boilerplate_keywords = [
        "terms and conditions", "privacy policy", "copyright",
        "all rights reserved", "disclaimer", "legal notice",
        "cookie policy", "end user license agreement"
    ]
    
    boilerplate_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        if any(keyword in chunk_lower for keyword in boilerplate_keywords):
            boilerplate_chunks.append(i)
    
    print(f"  Potential boilerplate chunks: {len(boilerplate_chunks)}")
    
    # Empty or near-empty chunks
    empty_chunks = [i for i, chunk in enumerate(chunks) if len(chunk.strip()) < 50]
    print(f"  Nearly empty chunks (< 50 chars): {len(empty_chunks)}")
    
    return {
        'short_chunks': short_chunks,
        'long_chunks': long_chunks,
        'boilerplate_chunks': boilerplate_chunks,
        'empty_chunks': empty_chunks,
        'source_counts': source_counts
    }

def show_sample_chunks(chunks, metadatas, indices, title, max_samples=3):
    """Show sample chunks from given indices."""
    print(f"\n{title}")
    print("-" * len(title))
    
    for i, idx in enumerate(indices[:max_samples]):
        if i >= max_samples:
            break
        print(f"\n[Sample {i+1}] Source: {metadatas[idx].get('source', 'Unknown')}")
        print(f"Words: {len(chunks[idx].split())}")
        print(f"Content: {chunks[idx][:200]}{'...' if len(chunks[idx]) > 200 else ''}")

def search_and_analyze(collection, query, n_results=10):
    """Perform a search and analyze the results."""
    print(f"\n🔍 SEARCH ANALYSIS FOR: '{query}'")
    print("="*50)
    
    results = collection.query(query_texts=[query], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    if not docs:
        print("No results found!")
        return
    
    print(f"Found {len(docs)} results")
    
    for i, (doc, meta, distance) in enumerate(zip(docs, metadatas, distances)):
        print(f"\n--- Result {i+1} (Distance: {distance:.3f}) ---")
        print(f"Source: {meta.get('source', 'Unknown')}")
        print(f"Words: {len(doc.split())}")
        print(f"Preview: {doc[:150]}...")
        
        # Check for competitive intelligence keywords
        competitive_keywords = [
            'pricing', 'price', 'cost', 'competitor', 'vs', 'versus', 
            'comparison', 'features', 'advantage', 'disadvantage',
            'market share', 'license', 'licensing'
        ]
        
        found_keywords = [kw for kw in competitive_keywords if kw.lower() in doc.lower()]
        if found_keywords:
            print(f"🎯 Competitive keywords found: {', '.join(found_keywords)}")

def main():
    parser = argparse.ArgumentParser(description="Debug ChromaDB collection quality")
    parser.add_argument("--search", type=str, help="Test search query")
    parser.add_argument("--limit", type=int, default=100, help="Max chunks to analyze")
    parser.add_argument("--show-samples", action="store_true", help="Show sample problematic chunks")
    args = parser.parse_args()
    
    try:
        # Connect to collection
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = get_competitor_collection(client)
        
        # Get collection stats
        total_count = collection.count()
        print(f"📊 COLLECTION OVERVIEW")
        print(f"Total chunks in collection: {total_count}")
        
        # Get sample of data for analysis
        limit = min(args.limit, total_count)
        sample_data = collection.get(limit=limit)
        
        chunks = sample_data.get("documents", [])
        metadatas = sample_data.get("metadatas", [])
        
        if not chunks:
            print("❌ No documents found in collection!")
            return
        
        # Analyze quality
        quality_issues = analyze_chunk_quality(chunks, metadatas)
        
        # Show samples if requested
        if args.show_samples:
            if quality_issues['short_chunks']:
                show_sample_chunks(chunks, metadatas, quality_issues['short_chunks'], 
                                 "🔸 SAMPLE SHORT CHUNKS:")
            
            if quality_issues['boilerplate_chunks']:
                show_sample_chunks(chunks, metadatas, quality_issues['boilerplate_chunks'], 
                                 "🔸 SAMPLE BOILERPLATE CHUNKS:")
        
        # Test search if provided
        if args.search:
            search_and_analyze(collection, args.search)
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("="*30)
        
        if len(quality_issues['short_chunks']) > len(chunks) * 0.1:
            print("• Consider increasing minimum chunk size during ingestion")
        
        if len(quality_issues['boilerplate_chunks']) > 0:
            print("• Consider filtering out boilerplate content during ingestion")
        
        if len(quality_issues['empty_chunks']) > 0:
            print("• Review document preprocessing to avoid empty chunks")
        
        # Source-specific recommendations
        output_chunks = sum(1 for source in quality_issues['source_counts'] if 'output' in source.lower())
        total_chunks = len(chunks)
        
        if output_chunks > total_chunks * 0.5:
            print("• High proportion of 'output' folder content - consider filtering for quality")
        
        print("\n🎯 SEARCH OPTIMIZATION TIPS:")
        print("• Use source filters to focus on high-quality documents")
        print("• Try different search modes (semantic vs keyword vs hybrid)")
        print("• Consider using the reranking feature for better relevance")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
