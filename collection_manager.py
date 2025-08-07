import chromadb
from ollama_embed import OllamaEmbeddingFunction




class CollectionManager:
    _instance = None

    def __new__(cls, db_path="chroma_db", model_name="nomic-embed-text:latest"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(db_path, model_name)
        return cls._instance

    def _init(self, db_path, model_name):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedding_fn = OllamaEmbeddingFunction(model_name=model_name)
        print(f"🔧 Using embedding model: {model_name}")
        self.collections = {}

    def get_collection(self, name: str, create_if_not_exists=True, metadata=None):
        if name in self.collections:
            return self.collections[name]
        try:
            collection = self.client.get_collection(
                name=name,
                embedding_function=self.embedding_fn
            )
        except Exception:
            if not create_if_not_exists:
                raise
            collection = self.client.create_collection(
                name=name,
                embedding_function=self.embedding_fn,
                metadata=metadata or {}
            )
        self.collections[name] = collection
        return collection

    def get_client(self):
        return self.client

    def get_shared_embedding_function():
        """
        Get the embedding function. Make sure this matches your available models!
        Run 'ollama list' to see what embedding models you have available.
        """
        # Try to use a proper embedding model if available
        # Common options: nomic-embed-text, all-minilm, mxbai-embed-large
        # here is the list of currently available models
        #llama3:instruct            365c0bd3c000    4.7 GB    2 weeks ago    
        #phi3:mini                  4f2222927938    2.2 GB    3 weeks ago    
        #command-r-plus:latest      e61b6b184f38    59 GB     3 weeks ago    
        #nomic-embed-text:latest    0a109f422b47    274 MB    4 weeks ago    
        #llama3:latest              365c0bd3c000    4.7 GB    4 weeks ago
        embedding_models = [
            "nomic-embed-text",      # Recommended - good for RAG
            "all-minilm",            # Lightweight option
            "mxbai-embed-large",     # High quality if you have resources
            "llama3"                 # Fallback to your current model
        ]
        
        # You should manually check which model works best
        # For now, using your current setup but you should consider switching
        model_name = "nomic-embed-text:latest"  # Change this to "nomic-embed-text" if you have it
        print(f"🔧 Using embedding model: {model_name}")
        return OllamaEmbeddingFunction(model_name=model_name)