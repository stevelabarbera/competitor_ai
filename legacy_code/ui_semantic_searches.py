import gradio as gr
from search_engine import ask

def ask_question(question, mode):
    return ask(question, mode)

iface = gr.Interface(
    fn=ask_question,
    inputs=[
        gr.Textbox(label="Ask a question"),
        gr.Radio(["semantic", "keyword", "hybrid", "full"], label="Mode", value="semantic")
    ],
    outputs=gr.Textbox(label="LLM Answer"),
    title="📊 Competitive Intelligence RAG UI",
    description="Query your local documents using semantic, keyword, hybrid, or full-context search."
)

if __name__ == "__main__":
    iface.launch()