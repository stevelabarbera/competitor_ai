
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
INTERNAL_DATA_DIR = ROOT_DIR / "internal_data"
OUTPUT_DIR = ROOT_DIR / "output"
FULL_CONTEXT_FILE = ROOT_DIR / "full_context.txt"

def collect_documents_from_directory(base_dir):
    documents = []
    for dirpath, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith((".txt", ".pdf")):
                full_path = Path(dirpath) / filename
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    company = Path(dirpath).relative_to(base_dir).parts[0]
                    documents.append((company, full_path, text))
                except Exception as e:
                    print(f"⚠️ Could not read {full_path}: {e}")
    return documents

def build_full_context():
    internal_docs = collect_documents_from_directory(INTERNAL_DATA_DIR)
    external_docs = collect_documents_from_directory(OUTPUT_DIR)

    with open(FULL_CONTEXT_FILE, "w", encoding="utf-8") as f:
        for source, docs in [("INTERNAL", internal_docs), ("EXTERNAL", external_docs)]:
            docs_by_company = {}
            for company, path, content in docs:
                docs_by_company.setdefault(company, []).append((path, content))
            for company, company_docs in docs_by_company.items():
                f.write(f"=== Source: {source} | Company: {company} ===\n\n")
                for path, content in company_docs:
                    f.write(f"--- Document: {path.name} ---\n{content}\n\n")

    print(f"✅ Full context written to: {FULL_CONTEXT_FILE}")

if __name__ == "__main__":
    build_full_context()
