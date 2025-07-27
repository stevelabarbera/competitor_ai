import os
import argparse
from pathlib import Path
from ingestion.semantic.vector_ingester import VectorIngester
from ingestion.semantic.memory_safe_company_ingester import MemorySafeCompanyIngester
from chunk_filtering.smart_chunker import SmartChunker

BASE_DIR = Path(__file__).resolve().parent
INTERNAL_DIR = BASE_DIR / "internal_documents"
OUTPUT_DIR = BASE_DIR / "output"

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
    parser.add_argument("--no-filter", action="store_true", help="Skip quality filtering")
    return parser.parse_args()

def gather_files(include_pdf=True, exclude_exts="") -> list:
    files = []
    exclude_exts = set(e.strip() for e in exclude_exts.split(",") if e.strip())
    for folder in [INTERNAL_DIR, OUTPUT_DIR]:
        for path in folder.glob("**/*"):
            if not path.is_file():
                continue
            ext = path.suffix.lower().lstrip(".")
            if ext in exclude_exts:
                continue
            if not include_pdf and path.suffix.lower() == ".pdf":
                continue
            files.append((str(path), path.name, 1))
    return files

def main():
    args = parse_arguments()
    print("🚀 Starting company-aware ingestion...")

    chunker = SmartChunker(chunk_size=args.chunk_size, overlap=args.overlap)
    ingester = MemorySafeCompanyIngester(
        chunkers=[chunker],
        quality_filter=not args.no_filter,
        batch_size=25,
        reset=args.reset_collection
    )

    files = gather_files(args.include_pdf, args.exclude_ext)
    if args.limit:
        files = files[:args.limit]

    if args.dry_run:
        print(f"🔍 DRY RUN: {len(files)} files selected for ingestion.")
    else:
        ingester.ingest_documents(files)
        print("✅ Ingestion complete.")

if __name__ == "__main__":
    main()
