def you():# fixed_ingestion.py (now using unified ingestion_driver_update)

import os
import chromadb
from datetime import datetime
from ingestion_driver_update import run_all_chunkers  # Our new driver
from embedding_config import get_competitor_collection

def flush_batch(collection, batch):
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
        for item in batch:
            try:
                collection.add(
                    documents=[item["text"]],
                    metadatas=[item["metadata"]],
                    ids=[item["id"]]
                )
            except Exception as individual_error:
                print(f"    ❌ Failed individual item {item['id']}: {individual_error}")

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
    exclude_exts = {f".{ext.strip().lower()}" for ext in exclude_ext.split("|") if ext.strip()}
    priority_dirs = [d.strip() for d in source_priority.split(",")]

    client = chromadb.PersistentClient(path="./chroma_db")
    if reset_collection:
        from embedding_config import reset_collection
        collection = reset_collection(client)
    else:
        collection = get_competitor_collection(client)

    all_files = []
    for root_dir in directories:
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                ext = os.path.splitext(filepath)[1].lower()
                if ext in exclude_exts:
                    continue
                if ext == ".txt" or (ext == ".pdf" and include_pdf):
                    priority = next((i for i, p in enumerate(priority_dirs) if p in filepath), len(priority_dirs))
                    all_files.append((filepath, filename, priority))

    all_files.sort(key=lambda x: x[2])

    chunk_count = 0
    file_count = 0
    batch = []

    for filepath, filename, priority in all_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except Exception as e:
            print(f"  ❌ Failed to read {filepath}: {e}")
            continue

        if not content or len(content) < 100:
            print(f"  ⚠️ Skipping short file: {filename}")
            continue

        print(f"  🗋 Chunking {filename} using all registered chunkers...")

        chunks = run_all_chunkers(content, filename, chunk_size=chunk_size, overlap=overlap)
        print(f"    🔢 Got {len(chunks)} chunks")

        for i, (text, metadata) in enumerate(chunks):
            chunk_id = f"{filename}_{i}_{file_count}"
            metadata.update({
                "source": filename,
                "full_path": filepath,
                "priority": priority,
                "file_size": os.stat(filepath).st_size,
                "ingestion_time": datetime.now().isoformat(),
            })
            batch.append({"text": text, "metadata": metadata, "id": chunk_id})

            chunk_count += 1
            if limit and chunk_count >= limit:
                flush_batch(collection, batch)
                return
            if len(batch) >= batch_size:
                flush_batch(collection, batch)
                batch.clear()

        file_count += 1

    flush_batch(collection, batch)
    print(f"\n🎉 Ingested {chunk_count} chunks from {file_count} files")

if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--include-pdf", action="store_true")
    parser.add_argument("--reset-collection", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ingest_documents_from_directories(
        directories=["internal_data", "output"],
        include_pdf=args.include_pdf,
        reset_collection=args.reset_collection,
        limit=args.limit,
        dry_run=args.dry_run
    )
