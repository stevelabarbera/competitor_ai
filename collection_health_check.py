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
                results['source_types'][meta