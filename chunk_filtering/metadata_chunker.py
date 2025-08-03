# chunk_filter.metadata_chunker.py
from abc import ABC, abstractmethod
from chunk_filtering.chunker import extract_metadata_from_content, chunk_text_smart
from company_metadata.tagging import parse_company_tags, normalize_company_name
from typing import List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataChunker(ABC):
    def __init__(self,file_name: str,file_content: str, chunk_size: int = 512, overlap: int = 64):
        self.file_name = file_name
        self.file_content = file_content
        self.chunk_size = chunk_size
        self.overlap = overlap

    @abstractmethod
    def chunk(self) -> List[Tuple[str, dict]]:
        pass

    def __call__(self, content: str, filename: str):
        self.file_content = content
        self.file_name = filename
        return self.chunk()


# would like to be able to chunk video converted to text crawler would provide the links in each respective content
class VideoChunker(MetadataChunker):
    def chunk(self) -> List[Tuple[str, dict]]: ...