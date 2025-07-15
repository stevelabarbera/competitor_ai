#fixed_ingestion.py
import os
import chromadb
import argparse
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from embedding_config import get_competitor_collection
from metadata_chunker import MetadataChunker  # Ensure your base class is here

os.environ['ONNX_DISABLE_COREML'] = '1'

def sanitize_metadata(metadata: dict) -> dict:
    sanitized = {}
    for k, v in metadata.items():
        if isinstance(v, list):
            sanitized[k] = ", ".join(map(str, v))
        else:
            sanitized[k] = v
    return sanitized

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ingest internal documents into ChromaDB with enhanced metadata")
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-pdf", action="store_true")
    parser.add_argument("--exclude-ext", type=str, default="")
    parser.add_argument("--reset-collection", action="store_true")
    parser.add_argument("--source-priority", type=str, default="internal_data")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()

def read_txt(path):
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read().strip()
        except UnicodeDecodeError:
            continue
    raise Exception(f"❌ Unable to decode file: {path}")

def read_pdf(path):
    try:
        with fitz.open(path) as doc:
            return "\n".join(f"[Page {i+1}]\n{page.get_text()}" for i, page in enumerate(doc) if page.get_text().strip())
    except Exception as e:
        print(f"⚠️ Failed to read PDF: {path} - {e}")
        return ""

def should_process_file(path, include_pdf, exclude_exts):
    ext = os.path.splitext(path)[1].lower()
    return ext == ".txt" or (ext == ".pdf" and include_pdf) if ext not in exclude_exts else False

def get_file_priority(path, priority_dirs):
    for i, p in enumerate(priority_dirs):
        if p in str(path):
            return i
    return len(priority_dirs)

def flush_batch(collection, batch):
    if not batch:
        return
    try:
        collection.add(
            documents=[i["text"] for i in batch],
            metadatas=[i["metadata"] for i in batch],
            ids=[i["id"] for i in batch],
        )
        print(f"✅ Flushed {len(batch)} chunks to DB")
    except Exception as e:
        print(f"❌ Batch flush failed: {e}")
        for item in batch:
            try:
                collection.add(
                    documents=[item["text"]],
                    metadatas=[item["metadata"]],
                    ids=[item["id"]],
                )
            except Exception as ind_err:
                print(f"  ❌ Failed to add: {item['id']} → {ind_err}")

def ingest_documents(
    directories,
    chunkers: list,
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
    collection = get_competitor_collection(client)

    print("🚀 Starting multi-chunker ingestion")

    all_files = []
    for root_dir in directories:
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                path = os.path.join(dirpath, f)
                if should_process_file(path, include_pdf, exclude_exts):
                    all_files.append((path, f, get_file_priority(path, priority_dirs)))

    all_files.sort(key=lambda x: x[2])
    print(f"📁 Found {len(all_files)} files")

    if dry_run:
        print("🔍 DRY RUN:")
        for f in all_files[:10]:
            print(f"  {f[0]}")
        return "Dry run done."

    file_count = 0
    chunk_count = 0
    batch = []
    for filepath, filename, priority in all_files:
        try:
            print(f"📄 {filepath}")
            content = read_pdf(filepath) if filepath.endswith(".pdf") else read_txt(filepath)

            # ✅ DEBUG: Check content type before calling .strip()
            print(f"🔍 Content type: {type(content)}")
            if isinstance(content, tuple):
                print(f"🚨 Unexpected tuple content: {content}")
                content = content[0]  # fallback for tuple-wrapped content

            if not isinstance(content, str):
                raise ValueError(f"❌ Content is not a string: {type(content)}")

            if not content.strip():
                print(f"⚠️ Skipped: too short")
                continue

            file_stats = os.stat(filepath)
            base_metadata = {
                "source": filename,
                "path": filepath,
                "priority": priority,
                "file_size": file_stats.st_size,
                "mod_time": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "ingested_at": datetime.now().isoformat()
            }

            for chunker_class in chunkers:
                chunker = chunker_class(
                    file_name=filename,
                    file_content=content,
                    chunk_size=chunk_size,
                    overlap=overlap
                )
                chunks = chunker.chunk()

                if not all(isinstance(c, tuple) and isinstance(c[0], str) for c in chunks):
                    raise TypeError(f"❌ Invalid chunk format returned: {chunks[:2]}")

                print(f"  🧩 {len(chunks)} chunks from {chunker.__class__.__name__}")
                for i, (chunk_text, metadata) in enumerate(chunks):
                    doc_id = f"{filename}_{chunker.__class__.__name__}_{i}_{file_count}"
                    combined_metadata = {**base_metadata, **metadata}
                    final_metadata = sanitize_metadata(combined_metadata)

                    if not chunk_text.strip():
                        continue

                    batch.append({
                        "text": chunk_text,
                        "metadata": final_metadata,
                        "id": doc_id
                    })
                    chunk_count += 1

                    if limit and chunk_count >= limit:
                        flush_batch(collection, batch)
                        print(f"🚨 LIMIT REACHED: {chunk_count} chunks")
                        break

                    if len(batch) >= batch_size:
                        flush_batch(collection, batch)
                        batch.clear()

            file_count += 1

        except Exception as e:
            print(f"❌ Error on {filepath}: {e}")
            continue


    flush_batch(collection, batch)
    return f"✅ Done. Files: {file_count}, Chunks: {chunk_count}"

if __name__ == "__main__":
    from metadata_chunker import DefaultChunker, CompanyChunker

    args = parse_arguments()

    result = ingest_documents(
        directories=["internal_data", "output"],
        chunkers=[DefaultChunker, CompanyChunker],
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        include_pdf=args.include_pdf,
        exclude_ext=args.exclude_ext,
        reset_collection=args.reset_collection,
        source_priority=args.source_priority,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    print(result)
