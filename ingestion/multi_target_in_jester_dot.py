import os
from pathlib import Path
from fixed_injection import should_process_file, get_file_priority

class MultiTargetIngester:
    def __init__(self, ingesters: list, config):
        self.ingesters = ingesters
        self.config = config

    def ingest_from_directories(self, directories: list):
        all_files = []
        for root_dir in directories:
            for dirpath, _, filenames in os.walk(root_dir):
                for f in filenames:
                    full_path = os.path.join(dirpath, f)
                    if should_process_file(full_path, self.config.include_pdf, self.config.exclude_exts):
                        all_files.append((full_path, f, get_file_priority(full_path, self.config.source_priority)))

        all_files.sort(key=lambda x: x[2])  # Priority sort
        self.ingest_documents(all_files)

    def ingest_documents(self, files: list):
        for ingester in self.ingesters:
            try:
                print(f"🚀 Running {ingester.__class__.__name__}.ingest_documents()")
                ingester.ingest_documents(files)
            except Exception as e:
                print(f"❌ Error in {ingester.__class__.__name__}.ingest_documents(): {e}")

    def flush_all(self):
        for ingester in self.ingesters:
            try:
                print(f"💾 Flushing {ingester.__class__.__name__}")
                ingester.flush_batch()
            except Exception as e:
                print(f"❌ Error flushing {ingester.__class__.__name__}: {e}")
