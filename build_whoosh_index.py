import os
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in
from whoosh.analysis import StemmingAnalyzer
from whoosh import index

# Paths
ROOT_DIR = Path(__file__).resolve().parent
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
INTERNAL_DATA_DIR = ROOT_DIR / "internal_data"
OUTPUT_DIR = ROOT_DIR / "output"

# Define schema
schema = Schema(
    company=ID(stored=True),
    path=ID(stored=True),
    content=TEXT(analyzer=StemmingAnalyzer(), stored=True)
)

# Document collector (from your existing logic)
def collect_documents_from_directory(base_dir):
    documents = []
    for dirpath, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith(".txt"):  # Ignore PDFs for Whoosh index
                full_path = Path(dirpath) / filename
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    company = Path(dirpath).relative_to(base_dir).parts[0]
                    documents.append((company, str(full_path), text))
                except Exception as e:
                    print(f"⚠️ Could not read {full_path}: {e}")
    return documents

# Build the index
def build_whoosh_index():
    if not WHOOSH_INDEX_DIR.exists():
        WHOOSH_INDEX_DIR.mkdir()

    ix = create_in(WHOOSH_INDEX_DIR, schema)
    writer = ix.writer()

    all_docs = collect_documents_from_directory(INTERNAL_DATA_DIR) + collect_documents_from_directory(OUTPUT_DIR)

    for company, path, content in all_docs:
        writer.add_document(company=company, path=path, content=content)

    writer.commit()
    print(f"✅ Whoosh index created with {len(all_docs)} documents.")

if __name__ == "__main__":
    build_whoosh_index()
