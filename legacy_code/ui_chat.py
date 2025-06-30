import gradio as gradiov
import chromadb
from chromadb.config import Settings
import subprocess
from whoosh.qparser import QueryParser
from whoosh import index as whoosh_index

# Connect to persistent ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="competitor_docs")

def keyword_search(question, top_k=5):
    ix = whoosh_index.open_dir("keyword_index")
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(question)
        results = searcher.search(query, limit=top_k)
        return [hit['content'] for hit in results]

def query_ollama(prompt):
    """Calls Ollama locally using subprocess."""
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def ask_question(question, mode):
    """Main logic for querying local data and LLM."""
    try:
        if mode == "RAG (Semantic Search)":
            results = collection.query(query_texts=[question], n_results=5)
            docs = results["documents"][0] if results["documents"] else []
            context = "\n\n".join(docs)
            final_prompt = f"{context}\n\nAnswer this question based on the context above:\n{question}"
        elif mode == "Full Context":
            with open("full_context.txt", "r") as f:
                context = f.read()
            final_prompt = f"{context}\n\nAnswer this question based on the full context above:\n{question}"
        else:
            return "❌ Invalid mode selected."

        answer = query_ollama(final_prompt)
        return answer

    except Exception as e:
        return f"❌ Error: {e}"

# Gradio Interface
iface = gr.Interface(
    fn=ask_question,
    inputs=[
        gr.Textbox(label="Ask a question about competitors or internal docs:"),
        gr.Dropdown(choices=["RAG (Semantic Search)", "Full Context"], label="Retrieval Mode", value="RAG (Semantic Search)")
    ],
    outputs=gr.Textbox(label="LLM Answer"),
    title="📊 Local Competitive Intelligence Chat",
    description="Choose your mode: retrieve chunks via vector search or load the entire full context file."
)

if __name__ == "__main__":
    iface.launch()
