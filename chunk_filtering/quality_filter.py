# chunk_filtering/quality_filter.py

from typing import List, Tuple
from .base import BaseChunkFilter

class QualityFilter(BaseChunkFilter):
    """Filters out low-quality chunks based on word count and boilerplate content."""

    def __init__(self, min_words: int = 50):
        self.min_words = min_words
        self.boilerplate_signals = [
            "terms and conditions", "privacy policy", "copyright",
            "all rights reserved", "disclaimer", "agreement",
            "legal notice", "cookie policy"
        ]

    def filter(self, chunks: List[Tuple[str, dict]]) -> List[Tuple[str, dict]]:
        """Apply filtering to remove short or boilerplate-like chunks."""
        result = []

        for chunk_text, metadata in chunks:
            if not isinstance(chunk_text, str):
                continue

            text = chunk_text.strip()
            if not text:
                continue

            words = text.split()
            if len(words) < self.min_words:
                continue

            chunk_lower = text.lower()
            if any(signal in chunk_lower for signal in self.boilerplate_signals):
                continue

            # Optional: Normalize whitespace
            cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            result.append((cleaned, metadata))

        return result
