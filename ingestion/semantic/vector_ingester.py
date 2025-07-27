#vector_ingester.py
import os
import chromadb
from datetime import datetime
from ingestion.base_ingestion import BaseIngester
from embedding_config import get_competitor_collection

class VectorIngester(BaseIngester):
    def __init__(self, chunkers, chroma_path="./chroma_db", collection_name="competitor_docs", quality_filter=True):
        super().__init__(chunkers, quality_filter)
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = get_competitor_collection(self.client, collection_name)
        self.batch = []

    def ingest_documents(self, files: list):
        for filepath, filename, priority in files:
            content = self.read_pdf(filepath) if filepath.endswith(".pdf") else self.read_txt(filepath)
            if not isinstance(content, str) or not content.strip():
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

            for chunker_class in self.chunkers:
                chunker = chunker_class(
                    file_name=filename,
                    file_content=content,
                    chunk_size=512,
                    overlap=64
                )
                chunks = chunker.chunk()

                if self.filter:
                    chunks = self.filter.filter(chunks)

                for i, (chunk_text, metadata) in enumerate(chunks):
                    if isinstance(chunk_text, tuple):
                        chunk_text = chunk_text[0]
                    if not isinstance(chunk_text, str) or not chunk_text.strip():
                        continue

                    doc_id = f"{filename}_{chunker.__class__.__name__}_{i}"
                    combined_metadata = {**base_metadata, **metadata}
                    final_metadata = self.sanitize_metadata(combined_metadata)

                    self.batch.append({
                        "text": chunk_text,
                        "metadata": final_metadata,
                        "id": doc_id
                    })

    def flush_batch(self):
        if not self.batch:
            return
        try:
            self.collection.add(
                documents=[i["text"] for i in self.batch],
                metadatas=[i["metadata"] for i in self.batch],
                ids=[i["id"] for i in self.batch],
            )
            print(f"✅ Flushed {len(self.batch)} chunks to ChromaDB")
        except Exception as e:
            print(f"❌ ChromaDB flush failed: {e}")
        self.batch.clear()
