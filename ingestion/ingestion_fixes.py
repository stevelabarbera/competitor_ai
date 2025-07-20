# Improved version of your ingestion logic
# Add these safety checks to your ingest_internal_doc.py

def flush_batch(batch):
    if not batch:
        return
    
    # Validate batch before adding to ChromaDB
    valid_items = []
    for item in batch:
        # Ensure all required fields exist and are valid
        if (item.get("text") and 
            item.get("metadata") and 
            item.get("id") and
            len(item["text"].strip()) > 10):  # minimum content length
            valid_items.append(item)
        else:
            print(f"⚠️ Skipping invalid chunk: {item.get('id', 'unknown')}")
    
    if valid_items:
        collection.add(
            documents=[item["text"] for item in valid_items],
            metadatas=[item["metadata"] for item in valid_items],
            ids=[item["id"] for item in valid_items],
        )
        print(f"✅ Flushed {len(valid_items)} valid chunks")
    else:
        print("❌ No valid chunks to flush")

# Also improve the chunk creation logic:
def create_chunk_safely(chunk, filename, idx):
    """Create a chunk with guaranteed valid metadata"""
    if not chunk or len(chunk.strip()) < 10:
        return None
    
    return {
        "text": chunk.strip(),
        "metadata": {
            "source": filename,
            "chunk_index": idx,
            "char_count": len(chunk),
            "word_count": len(chunk.split())
        },
        "id": f"{filename}_{idx}"
    }

# In your main ingestion loop, replace the chunk creation:
chunks = chunk_text(content, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
for idx, chunk in enumerate(chunks):
    chunk_item = create_chunk_safely(chunk, filename, idx)
    if chunk_item:  # only add valid chunks
        batch.append(chunk_item)
        chunk_count += 1
