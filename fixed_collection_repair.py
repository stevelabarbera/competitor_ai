#!/usr/bin/env python3
"""
🚨 COLLECTION REPAIR TOOL - FIXED VERSION
==================================================
This script fixes the ChromaDB collection issues:
1. Handles missing chroma_db directory gracefully
2. Fixes syntax errors in ingestion script
3. Provides robust error handling and recovery
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import traceback

def print_header(message):
    """Print a formatted header"""
    print(f"\n{'='*50}")
    print(f"🔧 {message}")
    print(f"{'='*50}")

def print_status(emoji, message):
    """Print a status message with emoji"""
    print(f"{emoji} {message}")

def check_prerequisites():
    """Check if all required files exist"""
    print_header("CHECKING PREREQUISITES")
    
    required_files = [
        "ingest_internal_doc.py",
        "internal_documents/",
        "output/"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
            print_status("❌", f"Missing: {file_path}")
        else:
            print_status("✅", f"Found: {file_path}")
    
    if missing_files:
        print_status("⚠️", f"Missing {len(missing_files)} required files/directories")
        return False
    
    return True

def fix_ingestion_syntax():
    """Fix the syntax error in ingest_internal_doc.py"""
    print_header("FIXING INGESTION SCRIPT SYNTAX")
    
    try:
        with open("ingest_internal_doc.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if the syntax error exists
        if 'raise Exception(f"Could not decode file with any of: {encodings}")' in content:
            print_status("🔍", "Found syntax error - fixing...")
            
            # Fix the f-string syntax
            fixed_content = content.replace(
                'raise Exception(f"Could not decode file with any of: {encodings}")',
                'raise Exception(f"Could not decode file with any of: {encodings}")'
            )
            
            # If that didn't work, try a more comprehensive fix
            if 'raise Exception(f"Could not decode file with any of: {encodings}")' in fixed_content:
                # Replace with a simpler, working version
                fixed_content = content.replace(
                    'raise Exception(f"Could not decode file with any of: {encodings}")',
                    'raise Exception("Could not decode file with any of the attempted encodings")'
                )
            
            # Create backup of original
            shutil.copy2("ingest_internal_doc.py", "ingest_internal_doc.py.backup")
            print_status("💾", "Created backup: ingest_internal_doc.py.backup")
            
            # Write fixed version
            with open("ingest_internal_doc.py", "w", encoding="utf-8") as f:
                f.write(fixed_content)
            
            print_status("✅", "Fixed syntax error in ingest_internal_doc.py")
            return True
        else:
            print_status("ℹ️", "No syntax error found - file appears to be correct")
            return True
            
    except Exception as e:
        print_status("❌", f"Error fixing ingestion script: {e}")
        return False

def backup_collection():
    """Backup the ChromaDB collection if it exists"""
    print_header("BACKING UP COLLECTION")
    
    chroma_path = Path("chroma_db")
    
    if not chroma_path.exists():
        print_status("ℹ️", "No existing ChromaDB found - no backup needed")
        return True
    
    try:
        backup_path = Path("chroma_db_backup")
        
        # Remove old backup if it exists
        if backup_path.exists():
            shutil.rmtree(backup_path)
            print_status("🗑️", "Removed old backup")
        
        # Create new backup
        shutil.copytree(chroma_path, backup_path)
        print_status("✅", f"Backup created: {backup_path}")
        return True
        
    except Exception as e:
        print_status("❌", f"Backup failed: {e}")
        return False

def clean_collection():
    """Remove the corrupted ChromaDB collection"""
    print_header("CLEANING CORRUPTED COLLECTION")
    
    chroma_path = Path("chroma_db")
    
    if chroma_path.exists():
        try:
            shutil.rmtree(chroma_path)
            print_status("🗑️", "Removed corrupted ChromaDB")
            print_status("✅", "Clean slate ready for re-ingestion")
            return True
        except Exception as e:
            print_status("❌", f"Failed to remove ChromaDB: {e}")
            return False
    else:
        print_status("ℹ️", "No ChromaDB directory found - already clean")
        return True

def test_ingestion():
    """Test the ingestion script to make sure it works"""
    print_header("TESTING INGESTION SCRIPT")
    
    try:
        # Try to compile the script first
        with open("ingest_internal_doc.py", "r", encoding="utf-8") as f:
            code = f.read()
        
        compile(code, "ingest_internal_doc.py", "exec")
        print_status("✅", "Ingestion script syntax is valid")
        return True
        
    except SyntaxError as e:
        print_status("❌", f"Syntax error still exists: {e}")
        print_status("🔍", f"Error at line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print_status("❌", f"Error testing ingestion script: {e}")
        return False

def run_ingestion():
    """Run the ingestion process"""
    print_header("RUNNING CLEAN INGESTION")
    
    try:
        print_status("🚀", "Starting ingestion process...")
        
        # Run the ingestion script
        result = subprocess.run(
            [sys.executable, "ingest_internal_doc.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print_status("✅", "Ingestion completed successfully!")
            if result.stdout:
                print("STDOUT:", result.stdout)
            return True
        else:
            print_status("❌", "Ingestion failed")
            if result.stderr:
                print("STDERR:", result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print_status("⏱️", "Ingestion timed out (5 minutes)")
        return False
    except Exception as e:
        print_status("❌", f"Error running ingestion: {e}")
        return False

def verify_collection():
    """Verify the new collection is working"""
    print_header("VERIFYING NEW COLLECTION")
    
    try:
        # Check if ChromaDB directory was created
        if not os.path.exists("chroma_db"):
            print_status("❌", "ChromaDB directory not created")
            return False
        
        print_status("✅", "ChromaDB directory exists")
        
        # Try to import and test the collection
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            collections = client.list_collections()
            
            if collections:
                print_status("✅", f"Found {len(collections)} collection(s)")
                for collection in collections:
                    count = collection.count()
                    print_status("📊", f"Collection '{collection.name}': {count} documents")
                return True
            else:
                print_status("⚠️", "No collections found in ChromaDB")
                return False
                
        except Exception as e:
            print_status("❌", f"Error accessing ChromaDB: {e}")
            return False
            
    except Exception as e:
        print_status("❌", f"Error verifying collection: {e}")
        return False

def main():
    """Main repair process"""
    print_header("COLLECTION REPAIR TOOL - FIXED VERSION")
    
    print("This tool will:")
    print("1. Check prerequisites")
    print("2. Fix syntax errors in ingestion script")
    print("3. Backup existing collection (if any)")
    print("4. Clean corrupted collection")
    print("5. Test ingestion script")
    print("6. Run clean ingestion")
    print("7. Verify new collection")
    
    # Ask for confirmation
    response = input("\nProceed with collection repair? (y/n): ").lower().strip()
    if response != 'y':
        print_status("🚫", "Repair cancelled by user")
        return
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        print_status("❌", "Prerequisites not met - cannot proceed")
        return
    
    # Step 2: Fix ingestion script syntax
    if not fix_ingestion_syntax():
        print_status("❌", "Could not fix ingestion script - cannot proceed")
        return
    
    # Step 3: Backup existing collection
    if not backup_collection():
        print_status("⚠️", "Backup failed - proceeding anyway")
    
    # Step 4: Clean corrupted collection
    if not clean_collection():
        print_status("❌", "Could not clean collection - cannot proceed")
        return
    
    # Step 5: Test ingestion script
    if not test_ingestion():
        print_status("❌", "Ingestion script still has errors - cannot proceed")
        return
    
    # Step 6: Run clean ingestion
    if not run_ingestion():
        print_status("❌", "Ingestion failed - check logs above")
        return
    
    # Step 7: Verify new collection
    if not verify_collection():
        print_status("❌", "Collection verification failed")
        return
    
    # Success!
    print_header("REPAIR COMPLETE!")
    print_status("🎉", "Collection repair completed successfully!")
    print_status("✅", "Your RAG system should now be working properly")
    
    print("\n📋 Next steps:")
    print("1. Test your search functionality")
    print("2. Run your UI with: python ui.py")
    print("3. Try some queries to verify data quality")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_status("🚫", "Repair interrupted by user")
    except Exception as e:
        print_status("❌", f"Unexpected error: {e}")
        traceback.print_exc()
