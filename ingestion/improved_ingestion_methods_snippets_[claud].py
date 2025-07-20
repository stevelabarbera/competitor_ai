# Add these improved functions to your ingest_internal_doc.py

def create_valid_metadata(filename, chunk_index, chunk_text):
    """Create guaranteed valid metadata for each chunk"""
    return {
        "source": filename,
        "chunk_index": chunk_index,
        "char_count": len(chunk_text),
        "word_count": len(chunk_text.split()),
        "file_type": os.path.splitext(filename)[1].lower()
    }

def validate_chunk(chunk_text, min_words=5):
    """Validate chunk meets minimum quality standards"""
    if not chunk_text or not isinstance(chunk_text, str):
        return False, "Empty or invalid chunk"
    
    clean_text = chunk_text.strip()
    if len(clean_text) < 20:
        return False, "Too short"
    
    words = clean_text.split()
    if len(words) < min_words:
        return False, f"Less than {min_words} words"
    
    return True, "Valid"

def flush_batch(batch):
    """Improved batch flushing with validation"""
    if not batch:
        return
    
    # Validate every item in batch
    valid_items = []
    for item in batch:
        # Check all required fields exist
        if not all(key in item for key in ["text", "metadata", "id"]):
            print(f"⚠️ Skipping chunk with missing fields: {item.get('id', 'unknown')}")
            continue
        
        # Validate text content
        is_valid, reason = validate_chunk(item["text"])
        if not is_valid:
            print(f"⚠️ Skipping invalid chunk {item['id']}: {reason}")
            continue
        
        # Validate metadata
        if not isinstance(item["metadata"], dict) or not item["metadata"].get("source"):
            print(f"⚠️ Skipping chunk with invalid metadata: {item['id']}")
            continue
        
        valid_items.append(item)
    
    if valid_items:
        try:
            collection.add(
                documents=[item["text"] for item in valid_items],
                metadatas=[item["metadata"] for item in valid_items],
                ids=[item["id"] for item in valid_items],
            )
            print(f"✅ Successfully added {len(valid_items)} valid chunks")
        except Exception as e:
            print(f"❌ Failed to add batch to ChromaDB: {e}")
    else:
        print("❌ No valid chunks in batch")

# Replace your main ingestion loop with this:
def ingest_documents_from_directories(directories, batch_size=50, chunk_size=None, overlap=None, include_pdf=None, exclude_ext=None):
    """Improved ingestion with comprehensive validation"""
    
    # Use parameters or fall back to global args
    chunk_size = chunk_size or CHUNK_SIZE
    overlap = overlap or OVERLAP
    include_pdf = include_pdf if include_pdf is not None else INCLUDE_PDF
    exclude_ext = exclude_ext or ""
    
    exclude_exts = {f".{ext.strip().lower()}" for ext in exclude_ext.split("|") if ext.strip()}
    
    chunk_count = 0
    batch = []
    processing_stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_created": 0,
        "chunks_valid": 0,
        "chunks_invalid": 0
    }

    for root_dir in directories:
        print(f"📁 Processing directory: {root_dir}")
        
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()

                # Skip excluded extensions
                if ext in exclude_exts:
                    processing_stats["files_skipped"] += 1
                    continue
                
                # Check if we should process this file type
                if not (ext == ".txt" or (include_pdf and ext == ".pdf")):
                    processing_stats["files_skipped"] += 1
                    continue

                filepath = os.path.join(dirpath, filename)
                print(f"📄 Processing: {filepath}")
                processing_stats["files_processed"] += 1

                # Read file content
                try:
                    if ext == ".pdf":
                        content = read_pdf(filepath)
                    else:
                        content = read_txt(filepath)
                except Exception as e:
                    print(f"⚠️ Failed to read {filename}: {e}")
                    continue

                if not content or len(content.strip()) < 50:
                    print(f"⚠️ Skipping {filename}: insufficient content")
                    continue

                # Create chunks
                chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
                processing_stats["chunks_created"] += len(chunks)
                
                for idx, chunk in enumerate(chunks):
                    # Validate chunk
                    is_valid, reason = validate_chunk(chunk)
                    if not is_valid:
                        processing_stats["chunks_invalid"] += 1
                        continue
                    
                    # Create validated chunk item
                    chunk_item = {
                        "text": chunk.strip(),
                        "metadata": create_valid_metadata(filename, idx, chunk),
                        "id": f"{filename}_{idx}"
                    }
                    
                    batch.append(chunk_item)
                    processing_stats["chunks_valid"] += 1
                    chunk_count += 1

                    # Check limits
                    if args.limit and chunk_count >= args.limit:
                        flush_batch(batch)
                        print("🔁 Limit reached, stopping.")
                        print_processing_stats(processing_stats)
                        return "Limit reached"

                    # Flush batch when full
                    if len(batch) >= batch_size:
                        flush_batch(batch)
                        batch.clear()

    # Flush remaining batch
    flush_batch(batch)
    
    # Print final stats
    print_processing_stats(processing_stats)
    return f"✅ Processed {processing_stats['files_processed']} files, added {processing_stats['chunks_valid']} chunks"

def print_processing_stats(stats):
    """Print processing statistics"""
    print("\n📊 PROCESSING STATISTICS")
    print("=" * 30)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files skipped: {stats['files_skipped']}")
    print(f"Chunks created: {stats['chunks_created']}")
    print(f"Chunks valid: {stats['chunks_valid']}")
    print(f"Chunks invalid: {stats['chunks_invalid']}")
    if stats['chunks_created'] > 0:
        validity_rate = (stats['chunks_valid'] / stats['chunks_created']) * 100
        print(f"Validity rate: {validity_rate:.1f}%")
