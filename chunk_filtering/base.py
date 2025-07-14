# chunk_filtering/base.py

from abc import ABC, abstractmethod
from typing import List

class BaseChunkFilter(ABC):
    """Abstract base class for post-retrieval chunk filtering."""

    @abstractmethod
    def filter(self, chunks: List[str]) -> List[str]:
        """Filter a list of text chunks based on specific logic."""
        pass
