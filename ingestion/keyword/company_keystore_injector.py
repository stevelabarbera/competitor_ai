#company_keystore_injector.py
from ingestion.base_ingester import BaseIngester
from company_keystore import CompanyKeystore
from pathlib import Path
from collections import defaultdict


class CompanyKeystoreIngester(KeywordIngester):
    def __init__(self, chunkers=None, keystore_dir="company_index", quality_filter=False):
        super().__init__(chunkers=[], quality_filter=quality_filter)
        self.keystore = CompanyKeystore(index_dir=keystore_dir)
        self.registry = defaultdict(lambda: {
            "aliases": set(),
            "document_count": 0
        })

    def ingest_documents(self, files: list):
        for filepath, filename, priority in files:
            company_id = extract_company_id(filepath)
            if company_id == "unknown":
                continue
            self.registry[company_id]["aliases"].update([company_id, f"{company_id}.com"])
            self.registry[company_id]["document_count"] += 1

    def extract_company_id(path: str) -> str:
        parts = Path(path).parts
        for part in parts:
            if "_com" in part:
                return part.replace("_com", "").replace("_", " ").lower()
        return "unknown"

    def flush_batch(self):
        records = []
        for cid, info in self.registry.items():
            records.append({
                "id": cid,
                "name": cid.title(),
                "aliases": list(info["aliases"]),
                "industry": "Unknown",
                "document_count": info["document_count"],
                "tags": [],
                "domain": f"{cid}.com"
            })
        self.keystore.populate_from_data(records)

if __name__ == "__main__":
keyword_store = CompanyKeystoreIngester()
keyword_store.ingest_documents(files)