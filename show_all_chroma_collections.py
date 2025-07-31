import chromadb

def list_chroma_collections(chroma_path: str = "./chroma_db") -> list[str]:
    """
    Return a list of collection names in the specified ChromaDB persistent directory.
    """
    client = chromadb.PersistentClient(path=chroma_path)
    return client.list_collections()

# Example usage:
if __name__ == "__main__":
    names = list_chroma_collections()
    print("ChromaDB Collections:")
    for name in names:
        print("  -", name)
