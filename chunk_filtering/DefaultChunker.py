#chunk_filter.DefaultChunker.py
from abc import ABC, abstractmethod
from improved_chunker import extract_metadata_from_content, chunk_text_smart
from company_metadata.tagging import parse_company_tags, normalize_company_name
from typing import List, Tuple


class DefaultChunker(MetadataChunker):
    def chunk(self) -> List[Tuple[str, dict]]:
        doc_metadata = extract_metadata_from_content(self.file_content, self.file_name)
        chunks = chunk_text_smart(self.file_content, self.chunk_size, self.overlap)
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = doc_metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_word_count": len(chunk.split())
            })
            result.append((chunk, chunk_metadata))
        return result
        
