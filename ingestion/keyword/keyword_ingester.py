#keyword_ingester.py
from ingestion.base_ingester import BaseIngester

class KeywordIngester(BaseIngester):
    def __init__(self, chunkers, index_path="whoosh_index", quality_filter=True):
        super().__init__(chunkers, quality_filter)
        self.index_path = index_path
        self.writer = None  # Will wire this up later with Whoosh logic

    def ingest_documents(self, files: list):
        print("KeywordIngester.ingest_documents() is not yet implemented.")

    def flush_batch(self):
        print("KeywordIngester.flush_batch() is not yet implemented.")
        