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
