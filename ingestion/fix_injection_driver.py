#fix_injection_driver.py
import argparse
from ingestion.ingest_config import IngestConfig
from ingestion.vector_ingester import VectorIngester
from ingestion.keyword_ingester import KeywordIngester
from ingestion.multi_target_ingester import MultiTargetIngester
from metadata_chunker import DefaultChunker, CompanyChunker

def parse_args():
    parser = argparse.ArgumentParser(description="Flexible ingestion entrypoint.")
    parser.add_argument("--directories", type=str, default="internal_data,output")
    parser.add_argument("--ingesters", type=str, default="vector")
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--include-pdf", action="store_true")
    parser.add_argument("--exclude-ext", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-filter", action="store_true")
    return parser.parse_args()

def build_config(args):
    return IngestConfig(
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        include_pdf=args.include_pdf,
        exclude_exts={f".{ext.strip().lower()}" for ext in args.exclude_ext.split("|") if ext.strip()},
        dry_run=args.dry_run,
        skip_filter=args.no_filter
    )

def main():
    args = parse_args()
    config = build_config(args)

    chunkers = [DefaultChunker, CompanyChunker]
    ingester_map = {
        "vector": VectorIngester(chunkers, quality_filter=not config.skip_filter),
        "keyword": KeywordIngester(chunkers, quality_filter=not config.skip_filter)
    }

    selected = [ingester_map[k.strip()] for k in args.ingesters.split(",") if k.strip() in ingester_map]
    multi = MultiTargetIngester(ingesters=selected, config=config)
    multi.ingest_from_directories([d.strip() for d in args.directories.split(",")])
    multi.flush_all()

if __name__ == "__main__":
    main()
