# chunk_filtering/base.py

from abc import ABC, abstractmethod
from typing import List

class BaseChunkFilter(ABC):
    """Abstract base class for post-retrieval chunk filtering."""

    #This may be a error I just added   +.second, close, window
    def __call__(self, content: str, filename: str):
        self.file_content = content
        self.file_name = filename
        return self.chunk()

    @abstractmethod
    def chunk(self, chunks: List[str]) -> List[str]:
        """Filter a list of text chunks based on specific logic."""
        pass
