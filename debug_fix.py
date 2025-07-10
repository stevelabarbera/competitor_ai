# Fix for the metadata error in your debug script
# Replace the problematic line with this safer version:

# Source distribution - handle None metadata safely
sources = [meta.get('source', 'Unknown') if meta is not None else 'No Metadata' for meta in metadatas]
source_counts = Counter(sources)

# Or alternatively, filter out None values first:
valid_metadatas = [meta for meta in metadatas if meta is not None]
sources = [meta.get('source', 'Unknown') for meta in valid_metadatas]
source_counts = Counter(sources)

# Also add this check to see how many chunks have missing metadata
none_count = sum(1 for meta in metadatas if meta is None)
print(f"📊 Chunks with missing metadata: {none_count}/{len(metadatas)}")
