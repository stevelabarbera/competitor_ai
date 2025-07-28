import os
from typing import List, Tuple, Optional
from pathlib import Path
import chromadb

from ingestion.base_ingestion import BaseIngester
from fixed_embedding_config import get_competitor_collection
from chunk_filtering.quality_filter import QualityFilter

class MemorySafeCompanyIngester(BaseIngester):
    def __init__(self, chunkers, chroma_path="./chroma_db", quality_filter=True,
                 batch_size=25, reset=False):
        super().__init__(chunkers, quality_filter)
        self.batch_size = batch_size
        self.reset = reset
        self.client = chromadb.PersistentClient(path=chroma_path)

    def clean_metadata(self, metadata: dict) -> dict:
        safe = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                safe[k] = v
            elif isinstance(v, list):
                safe[k] = ', '.join(map(str, v))
            else:
                safe[k] = str(v)
        return safe

    def ingest_documents(self, files: List[Tuple[str, str, Optional[int]]]):
        for filepath, filename, _priority in files:
            if not os.path.exists(filepath):
                continue

            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if len(content.strip()) < 50:
                continue

            chunks = self.apply_chunkers(content, filename)
            if self.quality_filter:
                filter = QualityFilter(min_words=50)
                chunks = filter.filter(chunks)

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
                batch.append((text, self.clean_metadata(meta)))

                if len(batch) >= self.batch_size:
                    self.flush_batch(collection, batch)
                    batch = []

            if batch:
                self.flush_batch(collection, batch)

    def flush_batch(self, collection, batch):
        try:
            documents, metadatas = zip(*batch)
            ids = [f"{meta['source']}_{meta['chunk_index']}" for meta in metadatas]
            collection.add(documents=list(documents), metadatas=list(metadatas), ids=ids)
        except Exception as e:
            print(f"❌ Failed to ingest batch: {e}")
