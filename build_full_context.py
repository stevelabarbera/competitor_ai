import os
from pathlib import Path
import fitz  # PyMuPDF
import traceback

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIRS = [
    BASE_DIR / "internal_data",
    BASE_DIR / "output",
]
CONTEXT_FILE = BASE_DIR / "full_context.txt"

def extract_text_from_pdf(path):
    try:
        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception:
        print(f"⚠️ Failed to read PDF: {path}")
        traceback.print_exc()
        return ""

def extract_text(path):
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        print(f"⚠️ Failed to read text file: {path}")
        return ""

def main():
    all_text = []

    for directory in OUTPUT_DIRS:
        for file_path in directory.rglob("*"):
            if file_path.suffix.lower() in [".txt", ".pdf"]:
                print(f"📄 Adding: {file_path}")
                content = extract_text(file_path)
                if content.strip():
                    header = f"\n\n### Source: {file_path.name}\n"
                    all_text.append(header + content.strip())

    full_text = "\n".join(all_text)
    CONTEXT_FILE.write_text(full_text, encoding="utf-8")
    print(f"\n✅ Full context written to: {CONTEXT_FILE}")
    print(f"📝 Total words: {len(full_text.split())}")

if __name__ == "__main__":
    main()
