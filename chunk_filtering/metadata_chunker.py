# chunk_filter.metadata_chunker.py
from abc import ABC, abstractmethod
from chunk_filtering.chunker import extract_metadata_from_content, chunk_text_smart
from company_metadata.tagging import parse_company_tags, normalize_company_name
from typing import List, Tuple

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

'''
currently deprecated cleaner data no longer empty primary_company & all_companies in our ingestion dataset
class CompanyChunker(MetadataChunker):
    def chunk(self) -> List[Tuple[str, dict]]:
        cleaned_text, company_tags = parse_company_tags(self.file_content)
        if not cleaned_text.strip():
            return []

        chunks = chunk_text_smart(cleaned_text, self.chunk_size, self.overlap)
        primary_company = None
        all_companies = list(company_tags)

        if company_tags:
            primary_company = all_companies[0]

        result = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": self.file_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_word_count": len(chunk.split())
            }

            if company_tags:
                metadata["primary_company"] = primary_company
                metadata["all_companies"] = all_companies
                metadata["company_normalized"] = normalize_company_name(primary_company)
                metadata["company_aliases"] = [normalize_company_name(c) for c in all_companies]

            content_lower = chunk.lower()
            if any(keyword in content_lower for keyword in ['price', 'pricing', 'cost', 'license']):
                metadata["content_type"] = "pricing"
            elif any(keyword in content_lower for keyword in ['feature', 'capability', 'functionality']):
                metadata["content_type"] = "features"
            elif any(keyword in content_lower for keyword in ['competitor', 'comparison', 'vs', 'versus']):
                metadata["content_type"] = "competitive"
            else:
                metadata["content_type"] = "general"

            if primary_company:
                metadata["content_type"] = f"{metadata['content_type']}_{normalize_company_name(primary_company)}"

            result.append((chunk, metadata))

        return result
'''
# would like to be able to chunk video converted to text crawler would provide the links in each respective content
class VideoChunker(MetadataChunker):
    def chunk(self) -> List[Tuple[str, dict]]: ...