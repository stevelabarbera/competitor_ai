from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from pathlib import Path
import os

# Setup paths
index_dir = "keyword_index"
context_file = "full_context.txt"

# Define schema
schema = Schema(
    title=ID(stored=True, unique=True),
    content=TEXT(stored=True)
)

# Create index directory
Path(index_dir).mkdir(exist_ok=True)

if not index.exists_in(index_dir):
    ix = index.create_in(index_dir, schema)
else:
    ix = index.open_dir(index_dir)

# Load context
with open(context_file, "r", encoding="utf-8") as f:
    full_text = f.read()

# Break into basic pseudo-documents by keyword sections or line count
chunks = full_text.split("\n\n")  # or use smarter segmentation later

# Index documents
writer = ix.writer()
for i, chunk in enumerate(chunks):
    if chunk.strip():
        writer.update_document(title=f"doc_{i}", content=chunk.strip())
writer.commit()

print(f"✅ Indexed {len(chunks)} keyword chunks into {index_dir}")
