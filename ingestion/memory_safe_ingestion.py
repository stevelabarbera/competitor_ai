# memory_safe_ingestion.py

from typing import List, Tuple, Callable
import time
import chromadb
from chromadb.config import Settings

# Example placeholder for chunk type
doc_chunk = Tuple[str, dict]

class MemorySafeIngestion:
    def __init__(self, batch_size: int = 20, delay_sec: float = 0.5):
        self.batch_size = batch_size
        self.delay_sec = delay_sec
        self.client = chromadb.PersistentClient(path="chroma_db")
        self.collection = self.client.get_or_create_collection(name="competitor_docs")

    def clean_metadata(self, metadata: dict) -> dict:
        """Ensure all metadata values are of types supported by ChromaDB (str, int, float, bool, None)."""
        def sanitize(v):
            if isinstance(v, list):
                return ", ".join(map(str, v))  # Convert list to comma-separated string
            elif isinstance(v, (str, int, float, bool)) or v is None:
                return v
            return str(v)

        return {k: sanitize(v) for k, v in metadata.items()}

    def ingest(self, chunks: List[doc_chunk], doc_prefix: str):
        """Flush chunks to ChromaDB in memory-safe batches."""
        batch = []

        for i, (chunk, metadata) in enumerate(chunks):
            doc_id = f"{doc_prefix}_{i}"
            metadata_cleaned = self.clean_metadata(metadata)

            batch.append({
                "ids": [doc_id],
                "documents": [chunk],
                "metadatas": [metadata_cleaned]
            })

            if len(batch) >= self.batch_size:
                self.flush_batch(batch)
                batch.clear()
                time.sleep(self.delay_sec)  # Let the system catch its breath

        # Final flush
        if batch:
            self.flush_batch(batch)

    def flush_batch(self, batch: List[dict]):
        try:
            for item in batch:
                self.collection.add(**item)
            print(f"✅ Flushed {len(batch)} chunks")
        except Exception as e:
            print(f"❌ Failed to flush batch: {e}")
            for item in batch:
                try:
                    self.collection.add(**item)
                except Exception as inner_e:
                    print(f"    ❌ Failed individual item {item['ids'][0]}: {inner_e}")

# Example driver usage
def run_memory_safe_ingestion(chunker_func: Callable):
    # Assume chunker_func returns List[Tuple[str, dict]]
    chunks = chunker_func()
    driver = MemorySafeIngestion(batch_size=10, delay_sec=3.0)
    driver.ingest(chunks, doc_prefix="safe_test")

# You can test with:
run_memory_safe_ingestion(lambda: [("This is a test chunk.", {"source": "test", "tags": ["example"]}) for _ in range(100)])
