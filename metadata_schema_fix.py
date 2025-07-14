#!/usr/bin/env python3
"""
Metadata Schema Fix Tool
========================
This script fixes ChromaDB metadata schema violations where list values
are being stored as metadata (which ChromaDB doesn't support).
"""

import chromadb
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('metadata_fix.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MetadataSchemaFixer:
    """Fixes ChromaDB metadata schema violations"""
    
    def __init__(self, chroma_path: str = "./chroma_db"):
        self.chroma_path = chroma_path
        self.client = None
        self.collection = None
        self.issues_found = defaultdict(int)
        
    def initialize(self, collection_name: str = "competitor_docs") -> bool:
        """Initialize ChromaDB connection"""
        try:
            if not os.path.exists(self.chroma_path):
                logger.error(f"ChromaDB directory not found: {self.chroma_path}")
                return False
            
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Connected to collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to ChromaDB: {e}")
            return False
    
    def is_valid_metadata_value(self, value: Any) -> bool:
        """Check if a value is valid for ChromaDB metadata"""
        # ChromaDB only allows: str, int, float, bool, None
        return isinstance(value, (str, int, float, bool, type(None)))
    
    def fix_metadata_value(self, key: str, value: Any) -> Any:
        """Fix invalid metadata values"""
        if self.is_valid_metadata_value(value):
            return value
        
        # Handle lists - convert to string representation
        if isinstance(value, list):
            self.issues_found['list_values'] += 1
            if all(isinstance(item, str) for item in value):
                # Join string lists with semicolons
                return "; ".join(value)
            else:
                # Convert mixed-type lists to JSON string
                return json.dumps(value)
        
        # Handle dictionaries - convert to JSON string
        elif isinstance(value, dict):
            self.issues_found['dict_values'] += 1
            return json.dumps(value)
        
        # Handle other types - convert to string
        else:
            self.issues_found['other_invalid_types'] += 1
            return str(value)
    
    def fix_metadata_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fix all invalid values in a metadata dictionary"""
        if not isinstance(metadata, dict):
            logger.warning(f"Invalid metadata type: {type(metadata)}")
            return {"source": "unknown", "error": "invalid_metadata_type"}
        
        fixed_metadata = {}
        
        for key, value in metadata.items():
            # Ensure key is string
            if not isinstance(key, str):
                key = str(key)
            
            # Fix the value
            fixed_value = self.fix_metadata_value(key, value)
            fixed_metadata[key] = fixed_value
        
        return fixed_metadata
    
    def get_all_documents(self) -> Optional[Dict]:
        """Get all documents from the collection"""
        try:
            total_count = self.collection.count()
            logger.info(f"Retrieving {total_count} documents...")
            
            # Get all documents in batches
            batch_size = 1000
            all_documents = []
            all_metadatas = []
            all_ids = []
            
            offset = 0
            while offset < total_count:
                batch = self.collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=['documents', 'metadatas']
                )
                
                all_documents.extend(batch['documents'])
                all_metadatas.extend(batch['metadatas'])
                all_ids.extend(batch['ids'])
                
                offset += batch_size
                logger.info(f"Retrieved {len(all_documents)}/{total_count} documents...")
            
            return {
                'documents': all_documents,
                'metadatas': all_metadatas,
                'ids': all_ids
            }
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return None
    
    def validate_and_fix_metadata(self, metadatas: List[Dict]) -> List[Dict]:
        """Validate and fix all metadata entries"""
        logger.info(f"Validating {len(metadatas)} metadata entries...")
        
        fixed_metadatas = []
        
        for i, metadata in enumerate(metadatas):
            try:
                if metadata is None:
                    logger.warning(f"None metadata at index {i}")
                    fixed_metadata = {"source": "unknown", "error": "none_metadata"}
                    self.issues_found['none_metadata'] += 1
                else:
                    fixed_metadata = self.fix_metadata_dict(metadata)
                
                fixed_metadatas.append(fixed_metadata)
                
                # Progress update
                if (i + 1) % 1000 == 0:
                    logger.info(f"Processed {i + 1}/{len(metadatas)} metadata entries...")
                    
            except Exception as e:
                logger.error(f"Error processing metadata at index {i}: {e}")
                fixed_metadatas.append({"source": "unknown", "error": "processing_error"})
                self.issues_found['processing_errors'] += 1
        
        return fixed_metadatas
    
    def backup_collection(self) -> bool:
        """Create a backup of the collection"""
        try:
            backup_path = Path("chroma_db_backup_before_metadata_fix")
            
            if backup_path.exists():
                import shutil
                shutil.rmtree(backup_path)
                logger.info("Removed old backup")
            
            import shutil
            shutil.copytree(self.chroma_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def recreate_collection_with_fixed_metadata(self, data: Dict) -> bool:
        """Recreate the collection with fixed metadata"""
        try:
            collection_name = self.collection.name
            
            # Delete the old collection
            logger.info("Deleting old collection...")
            self.client.delete_collection(collection_name)
            
            # Create new collection
            logger.info("Creating new collection...")
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Fix metadata
            logger.info("Fixing metadata...")
            fixed_metadatas = self.validate_and_fix_metadata(data['metadatas'])
            
            # Add documents back in batches
            batch_size = 100
            total_docs = len(data['documents'])
            
            for i in range(0, total_docs, batch_size):
                end_idx = min(i + batch_size, total_docs)
                
                batch_docs = data['documents'][i:end_idx]
                batch_metas = fixed_metadatas[i:end_idx]
                batch_ids = data['ids'][i:end_idx]
                
                # Validate batch before adding
                valid_batch_docs = []
                valid_batch_metas = []
                valid_batch_ids = []
                
                for doc, meta, doc_id in zip(batch_docs, batch_metas, batch_ids):
                    if doc and meta and doc_id:
                        valid_batch_docs.append(doc)
                        valid_batch_metas.append(meta)
                        valid_batch_ids.append(doc_id)
                
                if valid_batch_docs:
                    self.collection.add(
                        documents=valid_batch_docs,
                        metadatas=valid_batch_metas,
                        ids=valid_batch_ids
                    )
                
                logger.info(f"Added {end_idx}/{total_docs} documents...")
            
            logger.info("Collection recreated successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            return False
    
    def print_issues_summary(self):
        """Print summary of issues found and fixed"""
        logger.info("\n" + "="*50)
        logger.info("🔧 METADATA FIXES APPLIED")
        logger.info("="*50)
        
        if not self.issues_found:
            logger.info("✅ No metadata issues found!")
            return
        
        total_issues = sum(self.issues_found.values())
        logger.info(f"📊 Total Issues Fixed: {total_issues}")
        
        for issue_type, count in self.issues_found.items():
            logger.info(f"   {issue_type.replace('_', ' ').title()}: {count}")
        
        logger.info("\n💡 Issue Explanations:")
        if self.issues_found['list_values'] > 0:
            logger.info("   • List Values: Converted lists to semicolon-separated strings")
        if self.issues_found['dict_values'] > 0:
            logger.info("   • Dict Values: Converted dictionaries to JSON strings")
        if self.issues_found['none_metadata'] > 0:
            logger.info("   • None Metadata: Replaced with default metadata")
        if self.issues_found['other_invalid_types'] > 0:
            logger.info("   • Other Invalid Types: Converted to strings")
    
    def run_fix(self) -> bool:
        """Run the complete metadata fix process"""
        logger.info("🔧 Starting Metadata Schema Fix...")
        
        # Step 1: Get all documents
        logger.info("📥 Step 1: Retrieving all documents...")
        data = self.get_all_documents()
        if not data:
            logger.error("Failed to retrieve documents")
            return False
        
        # Step 2: Backup collection
        logger.info("💾 Step 2: Creating backup...")
        if not self.backup_collection():
            logger.error("Failed to create backup")
            response = input("Continue without backup? (y/n): ").lower().strip()
            if response != 'y':
                logger.info("Fix cancelled by user")
                return False
        
        # Step 3: Recreate collection with fixed metadata
        logger.info("🏗️ Step 3: Recreating collection with fixed metadata...")
        if not self.recreate_collection_with_fixed_metadata(data):
            logger.error("Failed to recreate collection")
            return False
        
        # Step 4: Print summary
        self.print_issues_summary()
        
        # Step 5: Verify the fix
        logger.info("✅ Step 5: Verifying fix...")
        final_count = self.collection.count()
        original_count = len(data['documents'])
        
        if final_count == original_count:
            logger.info(f"✅ Fix successful! Collection has {final_count} documents")
            return True
        else:
            logger.error(f"❌ Document count mismatch: {final_count} vs {original_count}")
            return False

def main():
    """Main fix process"""
    print("🔧 ChromaDB Metadata Schema Fix Tool")
    print("="*45)
    
    # Parse command line arguments
    collection_name = "competitor_docs"
    if '--collection' in sys.argv:
        try:
            idx = sys.argv.index('--collection')
            collection_name = sys.argv[idx + 1]
        except (IndexError, ValueError):
            print("❌ Invalid --collection argument")
            return False
    
    # Initialize fixer
    fixer = MetadataSchemaFixer()
    
    if not fixer.initialize(collection_name):
        return False
    
    # Show warning and get confirmation
    print("\n⚠️  WARNING: This tool will recreate your collection!")
    print("   • All documents will be temporarily removed and re-added")
    print("   • Metadata will be converted to valid ChromaDB format")
    print("   • A backup will be created before making changes")
    print("   • This process may take several minutes")
    
    response = input("\nProceed with metadata fix? (y/n): ").lower().strip()
    if response != 'y':
        print("🚫 Fix cancelled by user")
        return False
    
    # Run the fix
    success = fixer.run_fix()
    
    if success:
        print("\n🎉 Metadata schema fix completed successfully!")
        print("💡 You can now test your search functionality without metadata errors")
        return True
    else:
        print("\n❌ Metadata schema fix failed!")
        print("💡 Check the logs for details and restore from backup if needed")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🚫 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
