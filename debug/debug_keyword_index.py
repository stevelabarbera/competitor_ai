#!/usr/bin/env python3
"""
debug_keyword_index.py - Whoosh keyword index inspection utility
"""

from whoosh.index import open_dir
from whoosh.qparser import QueryParser  
from collections import Counter
import os

INDEX_DIR = "whoosh_index"  # Update if your index is elsewhere

def debug_index(index_dir):
    if not os.path.exists(index_dir):
        print(f"❌ Index directory not found: {index_dir}")
        return

    print(f"📂 Inspecting Whoosh index at: {index_dir}")
    try:
        ix = open_dir(index_dir)
        with ix.searcher() as searcher:
            total_docs = searcher.doc_count()
            print(f"📊 Total documents in index: {total_docs}")

            source_type_counts = Counter()
            company_counts = Counter()
            sources = Counter()

            for fields in searcher.all_stored_fields():
                source_type = fields.get("source_type", "Unknown")
                company = fields.get("company", "Unknown")
                source = fields.get("source", "Unknown")

                source_type_counts[source_type] += 1
                company_counts[company] += 1
                sources[source] += 1

            print("\n🏷️ Source Type Breakdown:")
            for k, v in source_type_counts.most_common():
                print(f"  {k}: {v}")

            print("\n🏢 Top Companies:")
            for k, v in company_counts.most_common(10):
                print(f"  {k}: {v}")

            print("\n📄 Top Source Files:")
            for k, v in sources.most_common(10):
                print(f"  {k}: {v}")

            print("\n✅ Index scan complete.")
    except Exception as e:
        print(f"⚠️ Debug Whoosh Exception - {e}")


if __name__ == "__main__":
    debug_index(INDEX_DIR)
