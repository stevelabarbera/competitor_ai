#!/usr/bin/env python3
"""
Collection Health Check Tool
============================
This script validates the health of your ChromaDB collection
and provides detailed diagnostics.
"""

import chromadb
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from collections import defaultdict, Counter

class CollectionHealthChecker:
    """Validates ChromaDB collection health"""
    
    def __init__(self, chroma_path: str = "./chroma_db"):
        self.chroma_path = chroma_path
        self.client = None
        self.collection = None
        
    def initialize(self, collection_name: str = "competitor_docs") -> bool:
        """Initialize ChromaDB connection"""
        try:
            if not os.path.exists(self.chroma_path):
                print(f"❌ ChromaDB directory not found: {self.chroma_path}")
                return False
            
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            try:
                self.collection = self.client.get_collection(name=collection_name)
                print(f"✅ Connected to collection: {collection_name}")
                return True
            except Exception as e:
                print(f"❌ Collection '{collection_name}' not found: {e}")
                
                # List available collections
                collections = self.client.list_collections()
                if collections:
                    print(f"📋 Available collections: {[c.name for c in collections]}")
                else:
                    print("📋 No collections found")
                return False
                
        except Exception as e:
            print(f"❌ Error connecting to ChromaDB: {e}")
            return False
    
    def get_basic_stats(self) -> Dict:
        """Get basic collection statistics"""
        try:
            total_docs = self.collection.count()
            
            # Get a sample of documents to analyze
            sample_size = min(100, total_docs)
            if sample_size > 0:
                sample_data = self.collection.get(limit=sample_size, include=['documents', 'metadatas'])
                
                return {
                    'total_documents': total_docs,
                    'sample_size': sample_size,
                    'sample_documents': sample_data.get('documents', []),
                    'sample_metadatas': sample_data.get('metadatas', [])
                }
            else:
                return {
                    'total_documents': 0,
                    'sample_size': 0,
                    'sample_documents': [],
                    'sample_metadatas': []
                }
        except Exception as e:
            print(f"❌ Error getting basic stats: {e}")
            return None
    
    def check_metadata_health(self, metadatas: List) -> Dict:
        """Check metadata health"""
        results = {
            'total_metadata_entries': len(metadatas),
            'none_metadata_count': 0,
            'empty_metadata_count': 0,
            'missing_source_count': 0,
            'valid_metadata_count': 0,
            'source_types': Counter(),
            'source_files': Counter(),
            'metadata_fields': Counter()
        }
        
        for meta in metadatas:
            # Check for None metadata
            if meta is None:
                results['none_metadata_count'] += 1
                continue
            
            # Check for empty metadata
            if not meta or not isinstance(meta, dict):
                results['empty_metadata_count'] += 1
                continue
            
            # Check for missing source
            if 'source' not in meta or not meta['source']:
                results['missing_source_count'] += 1
                continue
            
            # Valid metadata
            results['valid_metadata_count'] += 1
            
            # Count source types
            if 'source_type' in meta:
                results['source_types'][meta['source_type']] += 1
            
            # Count source files
            if 'source' in meta:
                source_file = Path(meta['source']).name
                results['source_files'][source_file] += 1
            
            # Count all metadata fields
            for field in meta.keys():
                results['metadata_fields'][field] += 1
        
        return results
    
    def check_document_health(self, documents: List[str]) -> Dict:
        """Check document content health"""
        results = {
            'total_documents': len(documents),
            'empty_documents': 0,
            'short_documents': 0,
            'valid_documents': 0,
            'average_length': 0,
            'min_length': float('inf'),
            'max_length': 0,
            'length_distribution': {
                'very_short': 0,    # < 50 chars
                'short': 0,         # 50-200 chars  
                'medium': 0,        # 200-1000 chars
                'long': 0,          # 1000-5000 chars
                'very_long': 0      # > 5000 chars
            }
        }
        
        if not documents:
            return results
        
        total_length = 0
        
        for doc in documents:
            if not doc:
                results['empty_documents'] += 1
                continue
                
            doc_length = len(doc)
            total_length += doc_length
            
            # Update min/max
            results['min_length'] = min(results['min_length'], doc_length)
            results['max_length'] = max(results['max_length'], doc_length)
            
            # Check length categories
            if doc_length < 50:
                results['length_distribution']['very_short'] += 1
                results['short_documents'] += 1
            elif doc_length < 200:
                results['length_distribution']['short'] += 1
                results['short_documents'] += 1
            elif doc_length < 1000:
                results['length_distribution']['medium'] += 1
                results['valid_documents'] += 1
            elif doc_length < 5000:
                results['length_distribution']['long'] += 1
                results['valid_documents'] += 1
            else:
                results['length_distribution']['very_long'] += 1
                results['valid_documents'] += 1
        
        # Calculate average
        if documents:
            results['average_length'] = total_length / len(documents)
            
        # Fix min_length if no documents
        if results['min_length'] == float('inf'):
            results['min_length'] = 0
        
        return results
    
    def print_health_report(self, stats: Dict, metadata_health: Dict, document_health: Dict):
        """Print comprehensive health report"""
        print("\n" + "="*60)
        print("🏥 COLLECTION HEALTH REPORT")
        print("="*60)
        
        # Basic Stats
        print(f"\n📊 BASIC STATISTICS")
        print(f"   Total Documents: {stats['total_documents']:,}")
        print(f"   Sample Size: {stats['sample_size']:,}")
        
        # Metadata Health
        print(f"\n🏷️  METADATA HEALTH")
        print(f"   Valid Metadata: {metadata_health['valid_metadata_count']:,} / {metadata_health['total_metadata_entries']:,}")
        print(f"   None Metadata: {metadata_health['none_metadata_count']:,}")
        print(f"   Empty Metadata: {metadata_health['empty_metadata_count']:,}")
        print(f"   Missing Source: {metadata_health['missing_source_count']:,}")
        
        # Metadata health percentage
        if metadata_health['total_metadata_entries'] > 0:
            health_pct = (metadata_health['valid_metadata_count'] / metadata_health['total_metadata_entries']) * 100
            print(f"   Health Score: {health_pct:.1f}%")
            
            if health_pct >= 95:
                print("   Status: ✅ EXCELLENT")
            elif health_pct >= 80:
                print("   Status: ✅ GOOD")
            elif health_pct >= 60:
                print("   Status: ⚠️ FAIR")
            else:
                print("   Status: ❌ POOR")
        
        # Source Types
        if metadata_health['source_types']:
            print(f"\n📁 SOURCE TYPES")
            for source_type, count in metadata_health['source_types'].most_common():
                print(f"   {source_type}: {count:,}")
        
        # Top Source Files
        if metadata_health['source_files']:
            print(f"\n📄 TOP SOURCE FILES")
            for source_file, count in metadata_health['source_files'].most_common(10):
                print(f"   {source_file}: {count:,} chunks")
        
        # Document Health
        print(f"\n📝 DOCUMENT HEALTH")
        print(f"   Valid Documents: {document_health['valid_documents']:,}")
        print(f"   Short Documents: {document_health['short_documents']:,}")
        print(f"   Empty Documents: {document_health['empty_documents']:,}")
        print(f"   Average Length: {document_health['average_length']:.0f} chars")
        print(f"   Length Range: {document_health['min_length']} - {document_health['max_length']:,} chars")
        
        # Length Distribution
        print(f"\n📏 LENGTH DISTRIBUTION")
        for category, count in document_health['length_distribution'].items():
            print(f"   {category.replace('_', ' ').title()}: {count:,}")
        
        # Overall Health Assessment
        print(f"\n🎯 OVERALL ASSESSMENT")
        
        issues = []
        if metadata_health['none_metadata_count'] > 0:
            issues.append(f"{metadata_health['none_metadata_count']} None metadata entries")
        if metadata_health['missing_source_count'] > 0:
            issues.append(f"{metadata_health['missing_source_count']} missing source fields")
        if document_health['empty_documents'] > 0:
            issues.append(f"{document_health['empty_documents']} empty documents")
        if document_health['short_documents'] > document_health['valid_documents']:
            issues.append("Too many short documents")
        
        if not issues:
            print("   ✅ Collection is healthy!")
            print("   🚀 Ready for production use")
        else:
            print("   ⚠️ Issues found:")
            for issue in issues:
                print(f"      - {issue}")
            
            print(f"\n💡 RECOMMENDATIONS:")
            if metadata_health['none_metadata_count'] > 0:
                print("   - Re-run ingestion with metadata validation")
            if document_health['short_documents'] > document_health['valid_documents']:
                print("   - Increase minimum chunk size")
                print("   - Filter out low-quality content")
            if document_health['empty_documents'] > 0:
                print("   - Add document validation during ingestion")
    
    def show_sample_data(self, stats: Dict, num_samples: int = 3):
        """Show sample documents and metadata"""
        print(f"\n🔍 SAMPLE DATA (showing {num_samples} examples)")
        print("="*60)
        
        documents = stats['sample_documents'][:num_samples]
        metadatas = stats['sample_metadatas'][:num_samples]
        
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            print(f"\n📄 Sample {i+1}:")
            print(f"   Length: {len(doc) if doc else 0} chars")
            print(f"   Metadata: {meta}")
            if doc:
                preview = doc[:200] + "..." if len(doc) > 200 else doc
                print(f"   Preview: {preview}")
            print("-" * 40)
    
    def run_health_check(self, show_samples: bool = False) -> bool:
        """Run complete health check"""
        print("🏥 Starting Collection Health Check...")
        
        # Get basic stats
        stats = self.get_basic_stats()
        if stats is None:
            return False
        
        print(f"📊 Analyzing {stats['total_documents']:,} documents...")
        
        # Check metadata health
        metadata_health = self.check_metadata_health(stats['sample_metadatas'])
        
        # Check document health  
        document_health = self.check_document_health(stats['sample_documents'])
        
        # Print comprehensive report
        self.print_health_report(stats, metadata_health, document_health)
        
        # Show samples if requested
        if show_samples:
            self.show_sample_data(stats)
        
        return True

def main():
    """Main health check process"""
    print("🏥 ChromaDB Collection Health Checker")
    print("="*40)
    
    # Parse command line arguments
    show_samples = '--samples' in sys.argv
    collection_name = "competitor_docs"
    
    # Check if custom collection name provided
    if '--collection' in sys.argv:
        try:
            idx = sys.argv.index('--collection')
            collection_name = sys.argv[idx + 1]
        except (IndexError, ValueError):
            print("❌ Invalid --collection argument")
            return False
    
    # Initialize checker
    checker = CollectionHealthChecker()
    
    if not checker.initialize(collection_name):
        print("\n💡 Usage:")
        print("   python collection_health_check.py [--collection NAME] [--samples]")
        print("   --collection: Specify collection name (default: competitor_docs)")
        print("   --samples: Show sample documents and metadata")
        return False
    
    # Run health check
    success = checker.run_health_check(show_samples)
    
    if success:
        print(f"\n✅ Health check completed successfully!")
        return True
    else:
        print(f"\n❌ Health check failed!")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🚫 Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)