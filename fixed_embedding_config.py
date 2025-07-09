# embedding_config.py
from ollama_embed import OllamaEmbeddingFunction
import chromadb

def get_shared_embedding_function():
    """
    Get the embedding function. Make sure this matches your available models!
    Run 'ollama list' to see what embedding models you have available.
    """
    # Try to use a proper embedding model if available
    # Common options: nomic-embed-text, all-minilm, mxbai-embed-large
    embedding_models = [
        "nomic-embed-text",      # Recommended - good for RAG
        "all-minilm",            # Lightweight option
        "mxbai-embed-large",     # High quality if you have resources
        "llama3"                 # Fallback to your current model
    ]
    
    # You should manually check which model works best
    # For now, using your current setup but you should consider switching
    model_name = "llama3"  # Change this to "nomic-embed-text" if you have it
    
    print(f"🔧 Using embedding model: {model_name}")
    return OllamaEmbeddingFunction(model_name=model_name)

def get_competitor_collection(client, create_if_not_exists=True):
    """
    Get or create the competitor collection with proper error handling.
    """
    collection_name = "competitor_docs"
    embedding_function = get_shared_embedding_function()
    
    try:
        # Try to get existing collection
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        print(f"✅ Found existing collection: {collection_name}")
        return collection
    
    except Exception as e:
        if create_if_not_exists:
            print(f"📝 Creating new collection: {collection_name}")
            collection = client.create_collection(
                name=collection_name,
                embedding_function=embedding_function,
                metadata={"description": "Competitive intelligence documents"}
            )
            return collection
        else:
            raise e

def reset_collection(client):
    """
    Reset the collection (useful if you want to start fresh).
    WARNING: This deletes all your data!
    """
    collection_name = "competitor_docs"
    
    try:
        # Delete existing collection
        client.delete_collection(name=collection_name)
        print(f"🗑️ Deleted collection: {collection_name}")
    except:
        print(f"ℹ️ Collection {collection_name} didn't exist")
    
    # Create fresh collection
    collection = get_competitor_collection(client, create_if_not_exists=True)
    print(f"✨ Created fresh collection: {collection_name}")
    return collection

def get_collection_info(client):
    """Get information about your collection."""
    try:
        collection = get_competitor_collection(client, create_if_not_exists=False)
        count = collection.count()
        
        print(f"📊 Collection Stats:")
        print(f"  Name: competitor_docs")
        print(f"  Total chunks: {count}")
        
        if count > 0:
            # Get a sample to show metadata structure
            sample = collection.get(limit=1, include=["metadatas"])
            if sample.get("metadatas"):
                print(f"  Sample metadata: {sample['metadatas'][0]}")
        
        return collection
    
    except Exception as e:
        print(f"❌ Error getting collection info: {e}")
        return None

if __name__ == "__main__":
    # Test the configuration
    client = chromadb.PersistentClient(path="./chroma_db")
    get_collection_info(client)
