import argparse
import chromadb
import os
from pathlib import Path
from chunker import chunk_text_with_metadata
from embedding_config import get_competitor_collection
import fitz  # PyMuPDF
from datetime import datetime

# ----------------------
# CLI argument parsing
# ----------------------
def parse_arguments():
    parser = argparse.ArgumentParser(description="Ingest internal documents into ChromaDB with enhanced metadata")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size (default: 512)")
    parser.add_argument("--overlap", type=int, default=64, help="Chunk overlap (default: 64)")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of chunks processed")
    parser.add_argument("--include-pdf", action="store_true", help="Include PDFs (default off)")
    parser.add_argument("--exclude-ext", type=str, default="", help="Pipe-delimited list of extensions to exclude (e.g. 'md|docx')")
    parser.add_argument("--reset-collection", action="store_true", help="Reset collection before ingestion")
    parser.add_argument("--source-priority", type=str, default="internal_data", help="Comma-separated list of directories in priority order")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be ingested without actually doing it")
    
    return parser.parse_args()

# ----------------------
# File reading utilities
# ----------------------
def read_txt(path):
    encodings = ['utf-8', 'latin-1', 'cp1252']  # Try multiple encodings
    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read().strip()
        except UnicodeDecodeError:
            continue
    raise Exception(f"Could not decode file with any of: {encodings}")

def read_pdf(path):
    try:
        with fitz.open(path) as doc:
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():  # Only add non-empty pages
                    text += f"\n[Page {page_num + 1}]\n{page_text}"
            return text.strip()
    except Exception as e:
        print(f"⚠️ Failed to read PDF: {path} - {e}")
        return ""

def get_file_priority(filepath, priority_dirs):
    """Assign priority based on directory."""
    for i, priority_dir in enumerate(priority_dirs):
        if priority_dir in str(filepath):
            return i
    return len(priority_dirs)  # Lowest priority for non-matching

def should_process_file(filepath, include_pdf, exclude_exts):
    """Determine if file should be processed."""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in exclude_exts:
        return False
    
    if ext == ".txt":
        return True
    elif ext == ".pdf" and include_pdf:
        return True
    
    return False

# ----------------------
# Enhanced ingestion with metadata
# ----------------------
def ingest_documents_from_directories(
    directories, 
    chunk_size=512, 
    overlap=64, 
    include_pdf=False, 
    exclude_ext="",
    reset_collection=False,
    source_priority="internal_data",
    limit=None,
    dry_run=False,
    batch_size=50
):
    """Enhanced document ingestion with better metadata and prioritization."""
    
    # Setup
    exclude_exts = {f".{ext.strip().lower()}" for ext in exclude_ext.split("|") if ext.strip()}
    priority_dirs = [d.strip() for d in source_priority.split(",")]
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="./chroma_db")
    
    if reset_collection:
        from embedding_config import reset_collection
        collection = reset_collection(client)
    else:
        collection = get_competitor_collection(client)
    
    print(f"🚀 Starting ingestion...")
    print(f"  Directories: {directories}")
    print(f"  Chunk size: {chunk_size}, Overlap: {overlap}")
    print(f"  Include PDFs: {include_pdf}")
    print(f"  Exclude extensions: {exclude_exts}")
    print(f"  Priority order: {priority_dirs}")
    print(f"  Dry run: {dry_run}")
    
    # Collect all files first for better progress tracking
    all_files = []
    
    for root_dir in directories:
        if not os.path.exists(root_dir):
            print(f"⚠️ Directory not found: {root_dir}")
            continue
            
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                
                if should_process_file(filepath, include_pdf, exclude_exts):
                    priority = get_file_priority(filepath, priority_dirs)
                    all_files.append((filepath, filename, priority))
    
    # Sort by priority (lower number = higher priority)
    all_files.sort(key=lambda x: x[2])
    
    print(f"📁 Found {len(all_files)} files to process")
    
    if dry_run:
        print("\n🔍 DRY RUN - Files that would be processed:")
        for filepath, filename, priority in all_files[:10]:  # Show first 10
            print(f"  Priority {priority}: {filepath}")
        if len(all_files) > 10:
            print(f"  ... and {len(all_files) - 10} more files")
        return "Dry run completed"
    
    # Process files
    chunk_count = 0
    file_count = 0
    batch = []
    failed_files = []
    
    for filepath, filename, priority in all_files:
        try:
            print(f"📄 Processing ({file_count + 1}/{len(all_files)}): {filepath}")
            
            # Read file content
            if filepath.endswith('.pdf'):
                content = read_pdf(filepath)
            else:
                content = read_txt(filepath)
            
            if not content or len(content.strip()) < 100:  # Skip very short files
                print(f"  ⚠️ Skipping (too short): {filename}")
                continue
            
            # Enhanced metadata
            file_stats = os.stat(filepath)
            base_metadata = {
                "source": filename,
                "full_path": filepath,
                "directory": os.path.dirname(filepath),
                "priority": priority,
                "file_size": file_stats.st_size,
                "modified_time": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "ingestion_time": datetime.now().isoformat(),
                "file_type": "pdf" if filepath.endswith('.pdf') else "text"
            }
            
            # Get chunks with metadata
            chunks_with_metadata = chunk_text_with_metadata(content, filename, chunk_size, overlap)
            
            print(f"  📊 Generated {len(chunks_with_metadata)} chunks")
            
            # Add to batch
            for chunk_idx, (chunk_text, chunk_metadata) in enumerate(chunks_with_metadata):
                # Merge file metadata with chunk metadata
                final_metadata = {**base_metadata, **chunk_metadata}
                
                doc_id = f"{filename}_{chunk_idx}_{file_count}"  # Ensure uniqueness
                
                batch.append({
                    "text": chunk_text,
                    "metadata": final_metadata,
                    "id": doc_id
                })
                
                chunk_count += 1
                
                # Check limits
                if limit and chunk_count >= limit:
                    flush_batch(collection, batch)
                    print(f"🔁 Reached limit of {limit} chunks")
                    return f"Processed {file_count + 1} files, {chunk_count} chunks (limit reached)"
                
                # Flush batch if full
                if len(batch) >= batch_size:
                    flush_batch(collection, batch)
                    batch.clear()
            
            file_count += 1
            
        except Exception as e:
            print(f"❌ Failed to process {filepath}: {e}")
            failed_files.append(filepath)
            continue
    
    # Flush remaining batch
    flush_batch(collection, batch)
    
    # Summary
    summary = f"""
✅ INGESTION COMPLETE
📁 Files processed: {file_count}
📊 Total chunks: {chunk_count}
❌ Failed files: {len(failed_files)}
"""
    
    if failed_files:
        summary += f"\nFailed files:\n" + "\n".join(f"  - {f}" for f in failed_files[:5])
        if len(failed_files) > 5:
            summary += f"\n  ... and {len(failed_files) - 5} more"
    
    print(summary)
    return summary

def flush_batch(collection, batch):
    """Flush a batch of documents to ChromaDB."""
    if not batch:
        return
    
    try:
        collection.add(
            documents=[item["text"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
            ids=[item["id"] for item in batch],
        )
        print(f"  ✅ Flushed {len(batch)} chunks to database")
    except Exception as e:
        print(f"  ❌ Failed to flush batch: {e}")
        # Try to add items individually to identify problematic ones
        for item in batch:
            try:
                collection.add(
                    documents=[item["text"]],
                    metadatas=[item["metadata"]],
                    ids=[item["id"]]
                )
            except Exception as individual_error:
                print(f"    ❌ Failed individual item {item['id']}: {individual_error}")

# ----------------------
# Entry point
# ----------------------
if __name__ == "__main__":
    args = parse_arguments()
    
    result = ingest_documents_from_directories(
        directories=["internal_data", "output"],
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        include_pdf=args.include_pdf,
        exclude_ext=args.exclude_ext,
        reset_collection=args.reset_collection,
        source_priority=args.source_priority,
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    print(f"\n{result}")
