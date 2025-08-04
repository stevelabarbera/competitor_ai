import os
import argparse
import logging
from pathlib import Path
from ingestion.semantic.memory_safe_company_ingester import MemorySafeCompanyIngester
from chunk_filtering.CompanyChunker import CompanyChunker # NEW

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INTERNAL_DIR = BASE_DIR / "internal_data"
OUTPUT_DIR = BASE_DIR / "output"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ingest documents with company-aware metadata into ChromaDB")
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-pdf", action="store_true")
    parser.add_argument("--exclude-ext", type=str, default="")
    parser.add_argument("--reset-collection", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-filter", action="store_true", help="Skip quality filtering")
    return parser.parse_args()

def gather_files(include_pdf=True, exclude_exts="") -> list:
    files = []
    exclude_exts = set(e.strip() for e in exclude_exts.split(",") if e.strip())
    for folder in [INTERNAL_DIR]:#[INTERNAL_DIR, OUTPUT_DIR]:
        logger.info(f"Attempting to enumerate the folder  {folder} ")
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
    logger.info("\n🚀 Starting company-aware ingestion...")

    chunkers = [CompanyChunker]  # Class-based chunker

    ingester = MemorySafeCompanyIngester(
        chunkers=chunkers,
        quality_filter=not args.no_filter,
        batch_size=25,
        reset=args.reset_collection
    )

    files = gather_files(args.include_pdf, args.exclude_ext)
    logger.info(f"Gathered {len(files)} files from the provided directories.")
    if args.limit:
        files = files[:args.limit]
        logger.info(f"Reduced the Number of Files based on the provided limits of {args.limit}")
    if args.dry_run:
        logger.infop(f"🔍 DRY RUN: {len(files)} files selected for ingestion.")
    else:
        logger.info(f"Starting ingestion of the provided documents...")
        ingester.ingest_documents(files)
        print("✅ Ingestion complete.")

if __name__ == "__main__":
    main()
