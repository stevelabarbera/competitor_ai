# improved_chunker.py
import re
from typing import List, Tuple

def chunk_text_smart(text: str, chunk_size: int = 512, overlap: int = 64, preserve_sentences: bool = True) -> List[str]:
    """
    Smart chunking that tries to preserve sentence boundaries and meaningful context.
    """
    if not text.strip():
        return []
    
    # Clean up the text
    text = re.sub(r'\s+', ' ', text.strip())
    
    if preserve_sentences:
        return _chunk_by_sentences(text, chunk_size, overlap)
    else:
        return _chunk_by_words(text, chunk_size, overlap)

def _chunk_by_sentences(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Chunk text by sentences to preserve context."""
    # Split into sentences (handles common abbreviations)
    sentence_endings = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(sentence_endings, text)
    
    if not sentences:
        return [text]
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_words = len(sentence.split())
        
        # If adding this sentence would exceed chunk size, finalize current chunk
        if current_word_count + sentence_words > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            
            # Start new chunk with overlap
            overlap_words = overlap
            overlap_sentences = []
            overlap_word_count = 0
            
            # Take sentences from the end of current chunk for overlap
            for i in range(len(current_chunk) - 1, -1, -1):
                sent = current_chunk[i]
                sent_word_count = len(sent.split())
                if overlap_word_count + sent_word_count <= overlap_words:
                    overlap_sentences.insert(0, sent)
                    overlap_word_count += sent_word_count
                else:
                    break
            
            current_chunk = overlap_sentences
            current_word_count = overlap_word_count
        
        current_chunk.append(sentence)
        current_word_count += sentence_words
    
    # Add final chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def _chunk_by_words(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Original word-based chunking as fallback."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def extract_metadata_from_content(text: str, filename: str) -> dict:
    """Extract useful metadata from document content."""
    metadata = {"source": filename}
    
    # Extract potential company names (capitalized words that might be companies)
    company_patterns = [
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|LLC|Ltd|Solutions|Technologies|Systems)\.?)\b',
        r'\b(?:Palo Alto|CrowdStrike|SentinelOne|Microsoft|IBM|Cisco|Fortinet|Check Point)\b'
    ]
    
    companies = set()
    for pattern in company_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        companies.update([match.strip() for match in matches])
    
    if companies:
        metadata["mentioned_companies"] = list(companies)[:5]  # Limit to top 5
    
    # Detect content type
    content_lower = text.lower()
    if any(keyword in content_lower for keyword in ['price', 'pricing', 'cost', 'license', 'subscription']):
        metadata["content_type"] = "pricing"
    elif any(keyword in content_lower for keyword in ['feature', 'capability', 'functionality']):
        metadata["content_type"] = "features"
    elif any(keyword in content_lower for keyword in ['competitor', 'comparison', 'vs', 'versus']):
        metadata["content_type"] = "competitive"
    else:
        metadata["content_type"] = "general"
    
    # Document quality indicators
    word_count = len(text.split())
    metadata["word_count"] = word_count
    
    # Check for boilerplate indicators
    boilerplate_indicators = [
        'terms and conditions', 'privacy policy', 'copyright',
        'all rights reserved', 'disclaimer', 'legal notice'
    ]
    
    if any(indicator in content_lower for indicator in boilerplate_indicators):
        metadata["likely_boilerplate"] = True
    
    return metadata

def chunk_text_with_metadata(text: str, filename: str, chunk_size: int = 512, overlap: int = 64) -> List[Tuple[str, dict]]:
    """
    Chunk text and return chunks with enhanced metadata.
    Returns list of (chunk_text, metadata) tuples.
    """
    # Extract document-level metadata
    doc_metadata = extract_metadata_from_content(text, filename)
    
    # Get chunks
    chunks = chunk_text_smart(text, chunk_size, overlap)
    
    # Create chunk-specific metadata
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

# Backward compatibility
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """Original function signature for backward compatibility."""
    return chunk_text_smart(text, chunk_size, overlap)

if __name__ == "__main__":
    # Test the chunker
    sample_text = """
    CrowdStrike Falcon is a cloud-native endpoint protection platform. The platform provides 
    real-time threat detection and response capabilities. CrowdStrike offers several pricing 
    tiers including Falcon Go, Falcon Pro, and Falcon Enterprise. 
    
    Pricing starts at $8.99 per endpoint per month for the basic tier. The enterprise tier 
    includes advanced threat hunting and custom IOC management features. Compared to 
    competitors like SentinelOne and Microsoft Defender, CrowdStrike is positioned as a 
    premium solution.
    """
    
    chunks_with_metadata = chunk_text_with_metadata(sample_text, "crowdstrike_analysis.txt")
    
    for i, (chunk, metadata) in enumerate(chunks_with_metadata):
        print(f"--- Chunk {i+1} ---")
        print(f"Content: {chunk[:100]}...")
        print(f"Metadata: {metadata}")
        print()
