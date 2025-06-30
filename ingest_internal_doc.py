import argparse
import chromadb
import os
from pathlib import Path
from chunker import chunk_text
from embedding_config import get_competitor_collection
import fitz  # PyMuPDF

# ----------------------
# CLI argument parsing
# ----------------------
parser = argparse.ArgumentParser(description="Ingest internal documents into ChromaDB")
parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size (default: 512)")
parser.add_argument("--overlap", type=int, default=64, help="Chunk overlap (default: 64)")
parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of chunks processed")
parser.add_argument("--include-pdf", action="store_true", help="Include PDFs (default off)")
parser.add_argument("--exclude-ext", type=str, default="", help="Pipe-delimited list of extensions to exclude (e.g. 'md|docx')")
args = parser.parse_args()

CHUNK_SIZE = args.chunk_size
OVERLAP = args.overlap
INCLUDE_PDF = args.include_pdf
EXCLUDE_EXTS = {f".{ext.strip().lower()}" for ext in args.exclude_ext.split("|") if ext.strip()}

# ----------------------
# Chroma client setup
# ----------------------
client = chromadb.PersistentClient(path="./chroma_db")
collection = get_competitor_collection(client)

# ----------------------
# File reading utilities
# ----------------------
def read_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def read_pdf(path):
    try:
        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc).strip()
    except Exception as e:
        print(f"⚠️ Failed to read PDF: {path} - {e}")
        return ""

# ----------------------
# Batching
# ----------------------
def flush_batch(batch):
    if not batch:
        return
    collection.add(
        documents=[item["text"] for item in batch],
        metadatas=[item["metadata"] for item in batch],
        ids=[item["id"] for item in batch],
    )
    print(f"✅ Flushed {len(batch)} chunks")

# ----------------------
# Ingestion loop
# ----------------------
def ingest_documents_from_directories(directories, batch_size=50):
    chunk_count = 0
    batch = []

    for root_dir in directories:
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()

                if ext in EXCLUDE_EXTS:
                    continue
                if not (ext == ".txt" or (INCLUDE_PDF and ext == ".pdf")):
                    continue

                filepath = os.path.join(dirpath, filename)
                print(f"📄 Processing: {filepath}")

                if ext == ".pdf":
                    content = read_pdf(filepath)
                else:
                    try:
                        content = read_txt(filepath)
                    except Exception as e:
                        print(f"⚠️ Failed to read {filename}: {e}")
                        continue

                if not content:
                    continue

                chunks = chunk_text(content, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
                for idx, chunk in enumerate(chunks):
                    doc_id = f"{filename}_{idx}"
                    batch.append({
                        "text": chunk,
                        "metadata": {"source": filename},
                        "id": doc_id
                    })
                    chunk_count += 1

                    if args.limit and chunk_count >= args.limit:
                        flush_batch(batch)
                        print("🔁 Limit reached, stopping.")
                        return

                    if len(batch) >= batch_size:
                        flush_batch(batch)
                        batch.clear()

    flush_batch(batch)
    print(f"📚 Total chunks added: {chunk_count}")

# ----------------------
# Entry point
# ----------------------
if __name__ == "__main__":
    ingest_documents_from_directories(["internal_data", "output"])
