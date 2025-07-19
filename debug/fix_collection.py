#!/usr/bin/env python3
"""
fix_collection.py - Repair corrupted ChromaDB collection
"""

import chromadb
import shutil
from pathlib import Path
from embedding_config import get_competitor_collection

# Configuration
ROOT_DIR = Path(__file__).resolve().parent
CHROMA_DB_PATH = ROOT_DIR / "chroma_db"
BACKUP_PATH = ROOT_DIR / "chroma_db_backup"

def backup_collection():
    """Backup current collection before fixing"""
    print("💾 Backing up current collection...")
    try:
        if BACKUP_PATH.exists():
            shutil.rmtree(BACKUP_PATH)
        shutil.copytree(CHROMA_DB_PATH, BACKUP_PATH)
        print("✅ Backup created successfully")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def nuke_and_rebuild():
    """Complete collection rebuild - safest option"""
    print("🧨 Nuking corrupted collection...")
    
    # Remove corrupted ChromaDB
    if CHROMA_DB_PATH.exists():
        shutil.rmtree(CHROMA_DB_PATH)
        print("🗑️  Removed corrupted ChromaDB")
    
    # Remove Whoosh index too (may also be corrupted)
    whoosh_path = ROOT_DIR / "whoosh_index"
    if whoosh_path.exists():
        shutil.rmtree(whoosh_path)
        print("🗑️  Removed Whoosh index")
    
    print("✅ Clean slate ready for re-ingestion")

def run_clean_ingestion():
    """Run ingestion with improved validation"""
    print("📥 Starting clean ingestion...")
    
    import subprocess
    result = subprocess.run([
        "python", "ingest_internal_doc.py", 
        "--chunk-size", "512",
        "--overlap", "64",
        "--include-pdf"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Clean ingestion completed")
        print("STDOUT:", result.stdout[-500:])  # Last 500 chars
    else:
        print("❌ Ingestion failed")
        print("STDERR:", result.stderr)
        return False
    
    return True

def verify_fix():
    """Verify the collection is now healthy"""
    print("🔍 Verifying fix...")
    
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = get_competitor_collection(client)
        
        # Quick health check
        sample = collection.get(limit=5)
        docs = sample.get('documents', [])
        metadatas = sample.get('metadatas', [])
        
        if not docs:
            print("❌ No documents found after fix")
            return False
        
        none_count = sum(1 for meta in metadatas if meta is None)
        if none_count > 0:
            print(f"❌ Still have {none_count} None metadata entries")
            return False
        
        # Check sample metadata
        print("✅ Sample documents after fix:")
        for i, (doc, meta) in enumerate(zip(docs[:3], metadatas[:3])):
            source = meta.get('source', 'Missing') if meta else 'None'
            word_count = len(doc.split())
            print(f"  {i+1}. [{source}] ({word_count} words): {doc[:100]}...")
        
        print("🎉 Collection appears healthy!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚨 COLLECTION REPAIR TOOL")
    print("=" * 50)
    
    # Step 1: Backup
    if not backup_collection():
        print("❌ Cannot proceed without backup")
        exit(1)
    
    # Step 2: Nuclear option
    print("\n" + "=" * 50)
    response = input("⚠️  This will DELETE your current collection. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Aborted by user")
        exit(1)
    
    nuke_and_rebuild()
    
    # Step 3: Clean re-ingestion
    print("\n" + "=" * 50)
    if not run_clean_ingestion():
        print("❌ Failed to re-ingest. Check your ingestion script.")
        exit(1)
    
    # Step 4: Verify
    print("\n" + "=" * 50)
    if verify_fix():
        print("🎉 COLLECTION SUCCESSFULLY REPAIRED!")
        print("💡 You can now run: python debug_collection.py")
    else:
        print("❌ Fix verification failed")
        print("💡 Backup available at:", BACKUP_PATH)