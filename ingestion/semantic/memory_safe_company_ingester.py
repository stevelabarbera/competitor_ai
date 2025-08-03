import os
import time
import logging
from typing import List, Tuple, Optional
import chromadb
from pathlib import Path
import time

from ingestion.base_ingestion import BaseIngester
from fixed_embedding_config import get_competitor_collection
from chunk_filtering.quality_filter import QualityFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#constants
MIN_CONTENT_LENGTH = 20


class MemorySafeCompanyIngester(BaseIngester):
    def __init__(self, chunkers, chroma_path="./chroma_db", quality_filter=True,
                 batch_size=25, reset=False, delay_sec=0):
        super().__init__(chunkers, quality_filter)
        self.batch_size = batch_size
        self.reset = reset
        self.delay_sec = delay_sec
        self.client = chromadb.PersistentClient(path=chroma_path)

    def ingest_documents(self, files: List[Tuple[str, str, Optional[int]]]):
        for filepath, filename, _priority in files:
            if not os.path.exists(filepath):
                continue
            
            logger.info("📁 Starting company ingestion for: %s", filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            logger.info("📏 Measuring content size for: %s (%d chars)", filename, len(content.strip()))
            if len(content.strip()) < MIN_CONTENT_LENGTH:
                continue
   

            chunks = self.apply_chunkers(content, filename)
            logger.info("✅ Chunkers have completed chunking content and have returned %d chunks.", len(chunks))
            if self.filter:
                logger.info("🧹 Applying filter to chunks...", len(chunks))
                chunks = self.filter.chunk(chunks)

            
            logger.info("🔹 Chunking complete — %d chunks from: %s", len(chunks), filename)
            company_collections = {}  # Cache of Chroma collections

            for i, (text, meta) in enumerate(chunks):
                if not isinstance(text, str) or len(text.strip()) < MIN_CONTENT_LENGTH:
                    logger.info(f"Enumerating chunk of text and found it to be either not a string: '{isinstance(text,str)}' or less then the minimum defined content length {text.strip()} < {MIN_CONTENT_LENGTH}")
                    continue

                company_id = meta.get("company_normalized", "unknown")
                if company_id not in company_collections:
                    logger.info(f'Unknown company_id {company_id} need to pull the default unknown collection and add content there')
                    company_collections[company_id] = get_competitor_collection(
                        self.client,
                        collection_name=f"docs_{company_id}"
                    )
                 

                meta.update({
                    "source": filename,
                    "chunk_index": i,
                    "company": company_id
                })

                sanitized = self.sanitize_metadata(meta)
                logger.info(f"sanitized metadata: {sanitized}")
                batch = [(text, sanitized)]
                logger.info(f"sanitized metadata ->[(text,sanitized)] -> batch: {batch}")
                logger.info(f"📤 Flushing {len(batch)} chunks to collection: docs_{company_id} with batches a maximum size of {self.batch_size} before each flush.")
                self.flush_batch(company_collections[company_id], batch)
                logger.info(f"Flushing batch# : {filename}, company_id: {company_id},index: {i}")

                if self.delay_sec:
                    time.sleep(self.delay_sec)
    '''

    def ingest_documents_deprecated(self, files: List[Tuple[str, str, Optional[int]]]):
        for filepath, filename, _priority in files:
            if not os.path.exists(filepath):
                continue

            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if len(content.strip()) < 50:
                continue

            chunks = self.apply_chunkers(content, filename)
            if self.filter:
                chunks = self.filter.filter(chunks)

            # Extract company from metadata
            company_id = "general"
            for _, meta in chunks:
                if meta.get("company_normalized"):
                    company_id = meta["company_normalized"]
                    break
            collection = get_competitor_collection(self.client, collection_name=f"docs_{company_id}")

            batch = []

            for i, (text, meta) in enumerate(chunks):
                if len(text.strip()) < 30:
                    continue
                meta.update({
                    "source": filename,
                    "chunk_index": i,
                    "company": company_id
                })
                batch.append((text, self.sanitize_metadata(meta)))

                if len(batch) >= self.batch_size:
                    self.flush_batch(collection, batch)
                    batch = []
                    if self.delay_sec:
                        time.sleep(self.delay_sec)

            if batch:
                self.flush_batch(collection, batch)
    '''
    def flush_batch(self, collection, batch):
        try:
            documents, metadatas = zip(*batch)
            ids = [f"{meta['source']}_{meta['chunk_index']}" for meta in metadatas]
            collection.add(documents=list(documents), metadatas=list(metadatas), ids=ids)
        except Exception as e:
            logger.info(f"❌ Failed to ingest batch: {e}")
            logger.info(f"🔍 Metadata sample: {metadatas[0] if metadatas else 'N/A'}")


