import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from chromadb.config import Settings

# Use same model as during ingestion
embedding_function = OllamaEmbeddingFunction(model_name="nomic-embed-text")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="competitor_docs", embedding_function=embedding_function)

def main():
    while True:
        question = input("❓ Enter your question (or type 'exit' to quit): ").strip()
        if question.lower() == "exit":
            break

        try:
            results = collection.query(
                query_texts=[question],
                n_results=5
            )

            print("\n📚 Top matching chunks:\n")
            for i in range(len(results["documents"][0])):
                doc = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                score = results["distances"][0][i]

                print(f"🔹 Match #{i + 1} (Score: {score:.4f})")
                print(f"📄 Source: {metadata.get('source', 'unknown')} ({metadata.get('directory', 'n/a')})")
                print(f"📝 Snippet: {doc.strip()[:300]}...\n")

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
