import os
from pathlib import Path
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD
from whoosh.analysis import StandardAnalyzer
from ingestion.base_ingester import BaseIngester

def extract_company_id(path: str) -> str:
    parts = Path(path).parts
    for part in parts:
        if "_com" in part:
            return part.replace("_com", "").replace("_", " ").lower()
    return "unknown"

class KeywordIngester(BaseIngester):
    def __init__(self, chunkers, index_path="whoosh_index", quality_filter=True):
        super().__init__(chunkers, quality_filter)
        self.index_path = index_path
        self.ix = self._get_or_create_index()

    def _get_or_create_index(self):
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path, exist_ok=True)
            schema = Schema(
                company=ID(stored=True),
                path=ID(stored=True),
                content=TEXT(analyzer=StandardAnalyzer(), stored=True),
                chunk_index=NUMERIC(stored=True),
                content_type=KEYWORD(stored=True),
                mentioned_companies=TEXT(stored=True),
                priority=NUMERIC(stored=True)
            )
            return create_in(self.index_path, schema)
        return open_dir(self.index_path)

    def ingest_documents(self, files: list):
        writer = self.ix.writer()
        for filepath, filename, priority in files:
            content = self.read_pdf(filepath) if filepath.endswith(".pdf") else self.read_txt(filepath)
            if not isinstance(content, str) or not content.strip():
                continue

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

                    writer.add_document(
                        company=extract_company_id(filepath),
                        path=filepath,
                        content=chunk_text,
                        chunk_index=i,
                        content_type=metadata.get("content_type", ""),
                        mentioned_companies=metadata.get("mentioned_companies", ""),
                        priority=priority
                    )
        writer.commit()

    def flush_batch(self):
        pass  # Already committed in ingest
