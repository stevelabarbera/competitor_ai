# chunk_filtering/quality_filter.py
import logging
from typing import List, Tuple
from .base import BaseChunkFilter


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
class QualityFilter(BaseChunkFilter):
    """Filters out low-quality chunks based on word count and boilerplate content."""

    def __init__(self, min_words: int = 50):
        self.min_words = min_words
        self.boilerplate_signals = [
            "terms and conditions", "privacy policy", "copyright",
            "all rights reserved", "disclaimer", "agreement",
            "legal snotice", "cookie policy"
        ]

    def chunk(self, chunks: List[Tuple[str, dict]]) -> List[Tuple[str, dict]]:
        """Apply filtering to remove short or boilerplate-like chunks."""
        result = []

        for chunk_text, metadata in chunks:
            logger.info(f"Starting a quality filter chunk of the data")
            if not isinstance(chunk_text, str):
                logger.info(f"quality filter chunk_text is not a string skipping chunking process")
                continue

            text = chunk_text.strip()
            if not text:
                logger.info(f"quality filter chunk_text.strip returns no data skipping chunking process")
                continue

            words = text.split()
            if len(words) < self.min_words:
                logger.info(f"quality filter text.strip returned total length of words {words} and was less then the defined minimum words {self.min_words} skipping chunking process")
                continue

            chunk_lower = text.lower()
            if any(signal in chunk_lower for signal in self.boilerplate_signals):
                logger.info(f"Lowered the chunked text and found under boilerplate_signals skipping chunking process chunk_lower: chunk_lawyerit chunk_lower: {chunk_lower}")
                continue

            # Optional: Normalize whitespace
            cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            logger.info(f"Chunk successfully pass to the quality filters and is getting any white space normalized before being added")
            result.append((cleaned, metadata))

        return result
