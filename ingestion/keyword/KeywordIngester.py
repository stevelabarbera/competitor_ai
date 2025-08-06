import os
import logging
from pathlib import Path
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD
from whoosh.analysis import StandardAnalyzer
from ingestion.base_ingestion import BaseIngester

# Paths
ROOT_DIR = Path(__file__).resolve().parents[2]
WHOOSH_INDEX_DIR = ROOT_DIR / "whoosh_index"
INTERNAL_DATA_DIR = ROOT_DIR / "internal_data"
OUTPUT_DIR = ROOT_DIR / "output"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class KeywordIngester(BaseIngester):
    def __init__(self, chunkers, index_path="whoosh_index", quality_filter=True):
        super().__init__(chunkers, quality_filter)
        self.index_path = index_path
        self.ix = self._get_or_create_index()

    def _get_or_create_index(self,schema):
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path, exist_ok=True)

            return create_in(self.index_path, schema)
        return open_dir(self.index_path)

    def ingest_documents(self, files: list):
        writer = self.ix.writer()
        for filepath, filename, priority in files:
            content = self.read_pdf(filepath) if filepath.endswith(".pdf") else self.read_txt(filepath)
            if not isinstance(content, str) or not content.strip():
                continue

            for chunker_class in self.chunkers:
                chunker = chunker_class(
                    file_name=filename,
                    file_content=content,
                    chunk_size=512,
                    overlap=64
                )
                chunks = chunker.chunk()
                if self.filter:
                    chunks = self.filter.filter(chunks)

                for i, (chunk_text, metadata) in enumerate(chunks):
                    if isinstance(chunk_text, tuple):
                        chunk_text = chunk_text[0]
                    if not isinstance(chunk_text, str) or not chunk_text.strip():

                    writer.update_document(title=f"doc_{i}", content=chunk.strip())

                    print(f"✅ Indexed {len(chunks)} keyword chunks into {self.index_path}")
                    writer.add_document( )
        writer.commit()
        print(f"✅ Whoosh index created with {len(all_docs)} documents.")


# Document collector (from your existing logic)
def _collect_documents_from_directory(base_dir):
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


def get_whoosh_index():
    if not WHOOSH_INDEX_DIR.exists():
        WHOOSH_INDEX_DIR.mkdir()

    #ix = create_in(WHOOSH_INDEX_DIR, schema)
    #writer = ix.writer()

    return all_docs = collect_documents_from_directory(INTERNAL_DATA_DIR) #+ collect_documents_from_directory(OUTPUT_DIR)


# Build the index currepntly just looking at internal data need to fix
def build_whoosh_index2():
    all_docs = _collect_documents_from_directory(INTERNAL_DATA_DIR)# + _collect_documents_from_directory(OUTPUT_DIR)
    ingest_documents(all_docs)
    #print(f"build_woosh_index -> collect_documents_from_directory() -> all_docs: {all_docs}")


if __name__ == "__main__":
    build_whoosh_index()
