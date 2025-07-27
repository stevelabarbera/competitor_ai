from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.index import create_in
from whoosh.analysis import StandardAnalyzer
from key_file_store import KeyFileStore
import os

schema = Schema(
    company=ID(stored=True),
    chunk_id=ID(stored=True),
    path=ID(stored=True),
    content=TEXT(analyzer=StandardAnalyzer(), stored=True),
    priority=NUMERIC(stored=True),
    content_type=ID(stored=True),
    source_type=ID(stored=True)
)

def index_from_keystore(jsonl_path="key_store.jsonl", index_path="whoosh_index"):
    from whoosh import index
    if not os.path.exists(index_path):
        os.makedirs(index_path)
        ix = create_in(index_path, schema)
    else:
        ix = index.open_dir(index_path)

    store = KeyFileStore(jsonl_path)
    store.load()
    writer = ix.writer()

    for entry in store.entries:
        writer.add_document(
            company=entry["company"],
            chunk_id=entry["chunk_id"],
            path=entry["metadata"]["path"],
            content=entry["metadata"].get("text", ""),  # optional
            priority=entry["metadata"].get("priority", 1),
            content_type=entry["metadata"].get("content_type", ""),
            source_type=entry["metadata"].get("source_type", "")
        )
    writer.commit()
    print(f"✅ Whoosh index rebuilt from key store ({len(store.entries)} chunks)")
