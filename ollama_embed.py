import requests
from chromadb.utils.embedding_functions import EmbeddingFunction

class OllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="nomic-embed-text", base_url="http://localhost:11434"):
        self.model = model_name
        self.base_url = base_url

    def __call__(self, input):
        # Ensure input is a list of strings
        if not isinstance(input, list):
            input = [input]

        embeddings = []
        for text in input:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            data = response.json()
            if "embedding" not in data:
                raise Exception(f"Embedding failed: {data}")
            embeddings.append(data["embedding"])

        return embeddings
