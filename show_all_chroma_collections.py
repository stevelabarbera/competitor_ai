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
               # Get documents without any filters first
        results = name.get(
            limit=10,
            include=['documents', 'metadatas']
        )
        
        print(f"✅ Retrieved {len(results['ids'])} documents")
        
        print(f"Name: {name}, Count: {name.count()}, Data: {results['documents']}, Metadatas: {results['metadatas']} ")
