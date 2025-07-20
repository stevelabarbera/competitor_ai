#full_context_tools.py
#python full_context_tools.py --company Censys
#python full_context_tools.py --max-tokens 8000
#python full_context_tools.py --view-stats


import os
import argparse
from pathlib import Path
import fitz  # PyMuPDF
import traceback
from collections import Counter
from typing import List

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIRS = [BASE_DIR / "internal_data", BASE_DIR / "output"]
CONTEXT_FILE = BASE_DIR / "full_context.txt"

# Utility to guess company from file path
def guess_company_from_path(path: Path) -> str:
    for part in path.parts:
        lowered = part.lower()
        if "tenable" in lowered:
            return "Tenable"
        if "censys" in lowered:
            return "Censys"
        if "paloalto" in lowered or "palo-alto" in lowered:
            return "PaloAlto"
    return "Unknown"

# Extract PDF text
def extract_text_from_pdf(path):
    try:
        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception:
        print(f"⚠️ Failed to read PDF: {path}")
        traceback.print_exc()
        return ""

# Extract text (PDF or TXT)
def extract_text(path):
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        print(f"⚠️ Failed to read text file: {path}")
        return ""

# Trim large context blocks to fit token limits
class PromptTrimmer:
    def __init__(self, max_tokens=8000):
        from transformers import GPT2TokenizerFast
        self.tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
        self.max_tokens = max_tokens

    def trim(self, blocks: List[str]) -> str:
        result = []
        token_count = 0
        for block in blocks:
            block_tokens = len(self.tokenizer.encode(block))
            if token_count + block_tokens > self.max_tokens:
                break
            result.append(block)
            token_count += block_tokens
        return "\n\n".join(result)

# Main build script with optional company filter
def build_full_context(company_filter=None, max_tokens=None):
    all_text = []
    all_blocks = []

    for directory in OUTPUT_DIRS:
        for file_path in directory.rglob("*"):
            if file_path.suffix.lower() in [".txt", ".pdf"]:
                company = guess_company_from_path(file_path)
                if company_filter and company_filter.lower() != company.lower():
                    continue
                print(f"📄 Adding: {file_path} | Company: {company}")
                content = extract_text(file_path)
                if content.strip():
                    header = f"\n\n### Source: {file_path.name} | Company: {company}\n"
                    block = header + content.strip()
                    all_blocks.append(block)

    if max_tokens:
        trimmer = PromptTrimmer(max_tokens)
        full_text = trimmer.trim(all_blocks)
    else:
        full_text = "\n".join(all_blocks)

    CONTEXT_FILE.write_text(full_text, encoding="utf-8")
    print(f"\n✅ Full context written to: {CONTEXT_FILE}")
    print(f"📝 Total words: {len(full_text.split())}")

# Summary stats view
def view_context_stats():
    try:
        text = CONTEXT_FILE.read_text(encoding="utf-8")
        word_count = len(text.split())
        lines = text.splitlines()
        sources = [line for line in lines if line.startswith("### Source:")]
        companies = [line.split("Company:")[-1].strip() for line in sources if "Company:" in line]
        company_counter = Counter(companies)

        print(f"\n📊 CONTEXT STATS")
        print(f"Total words: {word_count}")
        print(f"Total files: {len(sources)}")
        print("Company distribution:")
        for company, count in company_counter.most_common():
            print(f"- {company}: {count} files")
    except Exception as e:
        print(f"❌ Failed to read stats: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", help="Filter files to specific company", default=None)
    parser.add_argument("--max-tokens", type=int, default=None, help="Max token count (for prompt trimming)")
    parser.add_argument("--view-stats", action="store_true", help="View stats of full_context.txt")
    args = parser.parse_args()

    if args.view_stats:
        view_context_stats()
    else:
        build_full_context(company_filter=args.company, max_tokens=args.max_tokens)
