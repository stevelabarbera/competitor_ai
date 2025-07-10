import re
from typing import List, Tuple, Dict, Set

def parse_company_tags(text: str) -> Tuple[str, Set[str]]:
    """
    Extract company tags from document and return cleaned text + company set.
    
    Looks for lines like:
    Company_Names: Tenable,Tenable.com,Tenable_com,Tenablelabs
    Company_Names: Disney,ESPN,Pixar,Lucasfilm
    """
    company_tags = set()
    
    # Look for company tag lines
    company_pattern = r'^Company_Names:\s*(.+)$'
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        match = re.match(company_pattern, line.strip(), re.IGNORECASE)
        if match:
            # Extract company names
            company_string = match.group(1)
            companies = [c.strip() for c in company_string.split(',') if c.strip()]
            company_tags.update(companies)
            # Don't include the tag line in content
            continue
        else:
            cleaned_lines.append(line)
    
    cleaned_text = '\n'.join(cleaned_lines)
    return cleaned_text, company_tags

def normalize_company_name(name: str) -> str:
    """Normalize company name for consistent tagging."""
    # Convert to lowercase, remove special chars, standardize
    normalized = re.sub(r'[^\w\s]', '', name.lower())
    normalized = re.sub(r'\s+', '_', normalized.strip())
    return normalized

def chunk_text_with_company_context(
    text: str, 
    filename: str, 
    chunk_size: int = 512, 
    overlap: int = 64
) -> List[Tuple[str, dict]]:
    """
    Enhanced chunking that preserves company context.
    """
    # Extract company tags from document
    cleaned_text, company_tags = parse_company_tags(text)
    
    if not cleaned_text.strip():
        return []
    
    # Get base chunks
    from improved_chunker import chunk_text_smart
    chunks = chunk_text_smart(cleaned_text, chunk_size, overlap)
    
    # Process company tags
    primary_company = None
    all_companies = list(company_tags)
    
    if company_tags:
        # First company is primary
        primary_company = all_companies[0]
        print(f"📌 Document tagged with companies: {', '.join(all_companies)}")
        print(f"🏢 Primary company: {primary_company}")
    
    # Create chunks with company context
    result = []
    for i, chunk in enumerate(chunks):
        # Base metadata
        metadata = {
            "source": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "chunk_word_count": len(chunk.split())
        }
        
        # Add company context
        if company_tags:
            metadata["primary_company"] = primary_company
            metadata["all_companies"] = all_companies
            metadata["company_normalized"] = normalize_company_name(primary_company)
            metadata["company_aliases"] = [normalize_company_name(c) for c in all_companies]
        
        # Content type detection (with company context)
        content_lower = chunk.lower()
        if any(keyword in content_lower for keyword in ['price', 'pricing', 'cost', 'license']):
            metadata["content_type"] = "pricing"
        elif any(keyword in content_lower for keyword in ['feature', 'capability', 'functionality']):
            metadata["content_type"] = "features"
        elif any(keyword in content_lower for keyword in ['competitor', 'comparison', 'vs', 'versus']):
            metadata["content_type"] = "competitive"
        else:
            metadata["content_type"] = "general"
        
        # Add company-specific content type
        if primary_company:
            metadata["content_type"] = f"{metadata['content_type']}_{normalize_company_name(primary_company)}"
        
        result.append((chunk, metadata))
    
    return result

def search_by_company(collection, company_name: str, query: str = None, limit: int = 10):
    """
    Search for content from a specific company.
    """
    normalized_company = normalize_company_name(company_name)
    
    # Search filters
    where_clause = {
        "$or": [
            {"company_normalized": normalized_company},
            {"company_aliases": {"$in": [normalized_company]}}
        ]
    }
    
    if query:
        # Semantic search with company filter
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_clause,
            include=['documents', 'metadatas', 'distances']
        )
    else:
        # Just get all documents for this company
        results = collection.get(
            where=where_clause,
            limit=limit,
            include=['documents', 'metadatas']
        )
    
    return results

def get_company_summary(collection, company_name: str):
    """
    Get a summary of what content we have for a specific company.
    """
    normalized_company = normalize_company_name(company_name)
    
    where_clause = {
        "$or": [
            {"company_normalized": normalized_company},
            {"company_aliases": {"$in": [normalized_company]}}
        ]
    }
    
    try:
        results = collection.get(
            where=where_clause,
            include=['metadatas']
        )
        
        if not results['metadatas']:
            return f"No content found for {company_name}"
        
        # Analyze content
        content_types = {}
        sources = set()
        total_chunks = len(results['metadatas'])
        
        for metadata in results['metadatas']:
            if metadata:
                content_type = metadata.get('content_type', 'unknown')
                content_types[content_type] = content_types.get(content_type, 0) + 1
                sources.add(metadata.get('source', 'unknown'))
        
        summary = f"""
🏢 Company: {company_name}
📊 Total chunks: {total_chunks}
📁 Sources: {len(sources)} files
📋 Content breakdown:
"""
        for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            summary += f"  - {ctype}: {count} chunks\n"
        
        summary += f"\n📄 Source files: {', '.join(list(sources)[:5])}"
        if len(sources) > 5:
            summary += f" ... and {len(sources) - 5} more"
        
        return summary
        
    except Exception as e:
        return f"Error getting summary for {company_name}: {e}"

def list_all_companies(collection):
    """
    List all companies in the database.
    """
    try:
        results = collection.get(include=['metadatas'])
        companies = set()
        
        for metadata in results['metadatas']:
            if metadata and 'primary_company' in metadata:
                companies.add(metadata['primary_company'])
        
        return sorted(list(companies))
        
    except Exception as e:
        return f"Error listing companies: {e}"

# Example usage and testing
if __name__ == "__main__":
    # Test company tag parsing
    sample_text = """
Company_Names: Tenable,Tenable.com,Tenable_com,Tenablelabs

Tenable offers vulnerability management solutions with comprehensive scanning capabilities.
Their pricing starts at $2,500 per year for 100 assets. Key features include:
- Continuous vulnerability scanning
- Risk-based prioritization
- Compliance reportin

Compared to competitors like Qualys and Rapid7, Tenable focuses more on asset discovery.
"""
    
    print("🧪 Testing company tagging...")
    print(f"Total Number Companies: {', '.join(list(list_all_companies))}")
    chunks_with_metadata = chunk_text_with_company_context(sample_text, "tenable_analysis.txt")
    
    for i, (chunk, metadata) in enumerate(chunks_with_metadata):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Primary Company: {metadata.get('primary_company')}")
        print(f"All Companies: {metadata.get('all_companies')}")
        print(f"Content Type: {metadata.get('content_type')}")
        print(f"Content: {chunk}...")
