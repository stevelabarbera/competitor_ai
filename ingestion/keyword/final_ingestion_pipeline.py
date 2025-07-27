#final_ingestion_pipeline.py
import os
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Union

import chromadb
from whoosh import index
from whoosh.fields import Schema, TEXT, ID
from whoosh.analysis import StandardAnalyzer

from chunk_filtering.smart_chunker import SmartChunker  # or your preferred chunker
from embedding_config import get_competitor_collection
from company_tag_parser import CompanyTagParser

# ---------- Config ----------
ROOT_DIR = Path(__file__).resolve().parent
INTERNAL_DIR = ROOT_DIR / "internal_documents"
OUTPUT_DIR = ROOT_DIR / "output"
CHROMA_DB_DIR = ROOT_DIR / "chroma_db"
WHOOSH_DIR = ROOT_DIR / "whoosh_index"
MAX_CHUNKS = 1000

# ---------- Setup ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
collection = get_competitor_collection(client)

schema = Schema(path=ID(stored=True), content=TEXT(analyzer=StandardAnalyzer()))
if not os.path.exists(WHOOSH_DIR):
    os.mkdir(WHOOSH_DIR)
    ix = index.create_in(WHOOSH_DIR, schema)
else:
    ix = index.open_dir(WHOOSH_DIR)

company_parser = CompanyTagParser()
company_parser.load()  # Assumes it loads from a JSON config

def sanitize_metadata(metadata: Dict) -> Dict:
    safe_meta = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe_meta[k] = v
        elif isinstance(v, list):
            safe_meta[k] = ', '.join(map(str, v))
        else:
            safe_meta[k] = str(v)
    return safe_meta

def gather_files() -> List[Tuple[str, str]]:
    sources = [(INTERNAL_DIR, 'internal'), (OUTPUT_DIR, 'output')]
    files = []
    for dir_path, label in sources:
        for path in dir_path.glob("**/*"):
            if path.is_file() and path.suffix.lower() in {'.txt', '.md', '.pdf'}:
                files.append((str(path), label))
    return files

def process_and_index_file(filepath: str, source_label: str, chunker: SmartChunker, chunk_limit: int) -> int:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if len(content.strip()) < 100:
        logger.warning(f"Skipping too-short file: {filepath}")
        return 0

    filename = os.path.basename(filepath)
    chunks = chunker.chunk(content)

    writer = ix.writer()
    chunk_count = 0

    for i, (chunk, meta) in enumerate(chunks):
        if len(chunk.strip()) < 50:
            continue

        company = company_parser.identify_company(chunk)
        metadata = sanitize_metadata({
            "source": source_label,
            "filename": filename,
            "chunk_index": i,
            "company": company,
            **meta
        })

        try:
            collection.add(documents=[chunk], metadatas=[metadata], ids=[f"{filename}_{i}"])
        except Exception as e:
            logger.error(f"Failed to add chunk to Chroma: {e}")
            continue

        try:
            writer.add_document(path=filepath, content=chunk)
        except Exception as e:
            logger.warning(f"Whoosh indexing failed for {filepath}: {e}")

        chunk_count += 1
        if chunk_count >= chunk_limit:
            break

    writer.commit()
    return chunk_count

def run_ingestion():
    files = gather_files()
    chunker = SmartChunker(chunk_size=512, overlap=64)

    total_chunks = 0
    for filepath, label in files:
        chunked = process_and_index_file(filepath, label, chunker, MAX_CHUNKS)
        logger.info(f"{filepath}: {chunked} chunks indexed.")
        total_chunks += chunked

    logger.info(f"✅ Done. Total chunks indexed: {total_chunks}")

if __name__ == "__main__":
    run_ingestion()
