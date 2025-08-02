#chunk_filter.CompanyChunker.py

from abc import ABC, abstractmethod
from company_metadata.tagging import parse_company_tags, normalize_company_name
from chunk_filtering.chunker import extract_metadata_from_content, chunk_text_smart
from chunk_filtering.metadata_chunker import MetadataChunker
from typing import List, Tuple

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
                "chunk_word_count": len(chunk.split()),
                "primary_company": primary_company or None,
                "company_normalized": normalize_company_name(primary_company) if primary_company else None,
                "all_companies": all_companies,
                "company_aliases": [normalize_company_name(c) for c in all_companies] if all_companies else []
            }

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
