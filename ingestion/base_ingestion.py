#base_ingesture.py
from abc import ABC, abstractmethod
from chunk_filtering.quality_filter import QualityFilter
import logging
import os
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseIngester(ABC):
    def __init__(self, chunkers, quality_filter=True):
        self.chunkers = chunkers
        self.quality_filter = quality_filter
        self.filter = QualityFilter() if quality_filter else None

    @abstractmethod
    def ingest_documents(self, files: list):
        pass

    @abstractmethod
    def flush_batch(self):
        pass

    def sanitize_metadata(self, metadata: dict) -> dict:
        sanitized = {}
        for k, v in metadata.items():
            if isinstance(v, list):
                sanitized[k] = ", ".join(map(str, v))
            else:
                sanitized[k] = "" if v is None else v

        return sanitized

    def read_txt(self, path):
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(path, "r", encoding=enc) as f:
                    result = f.read()
                    if isinstance(result, tuple):
                        logger.info(f"Open the file {path} contents is instance of tuple and not text therefore taking the topfrom list")
                        result = result[0]

                    return result.strip()
            except UnicodeDecodeError:
                continue
        raise Exception(f"Unable to decode file: {path}")

    def read_pdf(self, path):
        try:
            import fitz  # PyMuPDF
            with fitz.open(path) as doc:
                result = "\n".join(f"[Page {i+1}]\n{page.get_text()}" for i, page in enumerate(doc) if page.get_text().strip())
                if isinstance(result, tuple):
                    result = result[0]
                return result
        except Exception as e:
            print(f"Failed to read PDF: {path} - {e}")
            return ""

    def should_process_file(self,path, include_pdf, exclude_exts):
        ext = os.path.splitext(path)[1].lower()
        return ext == ".txt" or (ext == ".pdf" and include_pdf) if ext not in exclude_exts else False
       
    def apply_chunkers(self, content, filename):
        chunks = []
        for chunker_class in self.chunkers:
            chunker = chunker_class(filename, content)  # instantiate with the actual data
            new_chunks = chunker.chunk()
            if new_chunks:
                chunks.extend(new_chunks)
        return chunks
