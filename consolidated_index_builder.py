import os
import shutil
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir, exists_in
from whoosh.analysis import StemmingAnalyzer
from whoosh import index

# Paths
ROOT_DIR = Path(__file__).resolve().parent
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
INTERNAL_DATA_DIR = ROOT_DIR / "internal_data"
OUTPUT_DIR = ROOT_DIR / "output"

# Define schema
SCHEMA = Schema(
    company=ID(stored=True),
    path=ID(stored=True),
    content=TEXT(analyzer=StemmingAnalyzer(), stored=True)
)

def collect_documents_from_directory(base_dir):
    """
    Collect documents from directory structure
    Returns: List of (company, path, content) tuples
    """
    documents = []
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"Warning: Directory {base_path} does not exist")
        return documents
    
    # Walk through all files in directory
    for file_path in base_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md']:
            try:
                # Extract company from directory structure
                # Assuming structure like: base_dir/company_name/...
                relative_path = file_path.relative_to(base_path)
                company = relative_path.parts[0] if relative_path.parts else "unknown"
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if content:  # Only add non-empty files
                    documents.append((company, str(file_path), content))
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    return documents

def create_fresh_index():
    """Create a completely new index, removing any existing one"""
    if WHOOSH_INDEX_DIR.exists():
        shutil.rmtree(WHOOSH_INDEX_DIR)
        print(f"Removed existing index at {WHOOSH_INDEX_DIR}")
    
    WHOOSH_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    ix = create_in(WHOOSH_INDEX_DIR, SCHEMA)
    print(f"Created fresh index at {WHOOSH_INDEX_DIR}")
    return ix

def build_whoosh_index(rebuild=False):
    """
    Build or rebuild the Whoosh index
    
    Args:
        rebuild: If True, completely recreate the index
    """
    try:
        # Create or open index
        if rebuild or not exists_in(WHOOSH_INDEX_DIR):
            ix = create_fresh_index()
        else:
            ix = open_dir(WHOOSH_INDEX_DIR)
            print(f"Opened existing index at {WHOOSH_INDEX_DIR}")
        
        # Collect documents from both directories
        print("Collecting documents...")
        internal_docs = collect_documents_from_directory(INTERNAL_DATA_DIR)
        output_docs = collect_documents_from_directory(OUTPUT_DIR)
        all_docs = internal_docs + output_docs
        
        print(f"Found {len(internal_docs)} docs in internal_data")
        print(f"Found {len(output_docs)} docs in output")
        print(f"Total documents: {len(all_docs)}")
        
        if not all_docs:
            print("Warning: No documents found to index!")
            return ix
        
        # Add documents to index
        print("Adding documents to index...")
        writer = ix.writer()
        
        for i, (company, path, content) in enumerate(all_docs):
            writer.add_document(
                company=company,
                path=path,
                content=content
            )
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"Indexed {i + 1} documents...")
        
        writer.commit()
        print(f"Successfully indexed {len(all_docs)} documents")
        
        return ix
        
    except Exception as e:
        print(f"Error building index: {e}")
        raise

def update_index_incremental(new_documents):
    """
    Add new documents to existing index without full rebuild
    
    Args:
        new_documents: List of (company, path, content) tuples
    """
    try:
        if not exists_in(WHOOSH_INDEX_DIR):
            print("No existing index found. Building fresh index...")
            return build_whoosh_index()
        
        ix = open_dir(WHOOSH_INDEX_DIR)
        writer = ix.writer()
        
        for company, path, content in new_documents:
            writer.add_document(
                company=company,
                path=path,
                content=content
            )
        
        writer.commit()
        print(f"Added {len(new_documents)} new documents to index")
        
        return ix
        
    except Exception as e:
        print(f"Error updating index: {e}")
        raise

def get_index_stats():
    """Get basic statistics about the index"""
    try:
        if not exists_in(WHOOSH_INDEX_DIR):
            return {"status": "No index found"}
        
        ix = open_dir(WHOOSH_INDEX_DIR)
        with ix.searcher() as searcher:
            doc_count = searcher.doc_count()
            
            # Get company counts using a simple search approach
            companies = {}
            from whoosh.query import Every
            
            # Get all documents by searching for everything
            results = searcher.search(Every(), limit=None)
            for hit in results:
                company = hit.get('company', 'unknown')
                companies[company] = companies.get(company, 0) + 1
        
        return {
            "status": "Index exists",inHere
            "total_documents": doc_count,
            "companies": companies,
            "index_path": str(WHOOSH_INDEX_DIR)
        }
        
    except Exception as e:
        return {"status": f"Error reading index: {e}"}

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Whoosh keyword index")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index from scratch")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_index_stats()
        print("Index Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        build_whoosh_index(rebuild=args.rebuild)

if __name__ == "__main__":
    main()