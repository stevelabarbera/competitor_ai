from metadata_chunker import DefaultChunker, CompanyChunker

# Now you can instantiate and use both chunkers like:
def run_all_chunkers(file_content, file_name, chunk_size=512, overlap=64):
    from metadata_chunker import DefaultChunker, CompanyChunker

    chunks = []

    for ChunkerClass in [DefaultChunker, CompanyChunker]:
        chunker = ChunkerClass(
            file_name=file_name,
            file_content=file_content,
            chunk_size=chunk_size,
            overlap=overlap
        )
        try:
            chunks.extend(chunker.chunk())
        except Exception as e:
            print(f"❌ Error while running {ChunkerClass.__name__}: {e}")

    return chunks

# Example usage (in ingestion logic):
if __name__ == "__main__":
    file_name = "example.txt"
    with open(file_name, "r") as f:
        file_content = f.read()

    combined_chunks = run_all_chunkers(file_name, file_content)

    for chunk_text, metadata in combined_chunks:
        print("Chunk:", chunk_text[:100], "...\nMetadata:", metadata, "\n")
