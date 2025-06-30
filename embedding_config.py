# embedding_config.py
from ollama_embed import OllamaEmbeddingFunction

def get_shared_embedding_function():
    # Adjust model name as needed
    return OllamaEmbeddingFunction(model_name="llama3")

def get_competitor_collection(client):
    return client.get_collection(
        name="competitor_docs",
        embedding_function=get_shared_embedding_function()
    )
