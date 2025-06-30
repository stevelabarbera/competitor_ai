import argparse
import os
from pathlib import Path

import fitz  # PyMuPDF

from your_ingest_module import ingest_internal_doc  # adjust if needed


def extract_pdf_text(file_path):
    try:
        doc = fitz.open(file_path)
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        print(f"[ERROR] Failed to extract text from {file_path}: {e}")
        return None

def ingest_folder(path, collection_name="internal_docs", recursive=False, extensions=None):
    files_ingested = 0
    base_path = Path(path)

    if recursive:
        files = base_path.rglob("*")
    else:
        files = base_path.glob("*")

    for file_path in files:
        if file_path.is_file():
            if extensions and file_path.suffix.lower() not in extensions:
                continue

            try:
                print(f"Ingesting {file_path}...")

                if file_path.suffix.lower() == ".pdf":
                    text = extract_pdf_text(file_path)
                    if text:
                        ingest_internal_doc(text, collection_name, metadata={"source": str(file_path)})
                        files_ingested += 1
                else:
                    ingest_internal_doc(str(file_path), collection_name)
                    files_ingested += 1

            except Exception as e:
                print(f"[ERROR] Failed to ingest {file_path}: {e}")

    print(f"\n✅ Done. Ingested {files_ingested} files into '{collection_name}' collection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a folder of documents into ChromaDB")
    parser.add_argument("--path", type=str, required=True, help="Path to the folder containing files to ingest")
    parser.add_argument("--collection", type=str, default="internal_docs", help="Name of the ChromaDB collection")
    parser.add_argument("--recursive", action="store_true", help="Recursively ingest files in subdirectories")
    parser.add_argument("--filter", type=str, help="Comma-separated list of file extensions to include (e.g., .txt,.md,.pdf)")

    args = parser.parse_args()

    ext_list = [e.strip().lower() for e in args.filter.split(",")] if args.filter else None

    ingest_folder(
        path=args.path,
        collection_name=args.collection,
        recursive=args.recursive,
        extensions=ext_list,
    )
