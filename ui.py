import gradio as gr
from search_engine import ask
from ingest_internal_doc import ingest_documents_from_directories

# === Ask/Answer logic ===
def ask_and_debug(question, mode):
    answer = ask(question, mode=mode)
    return answer, f"✅ Successfully answered using mode: {mode}"

# === Ingestion Trigger Function ===
def trigger_ingestion(chunk_size, overlap, include_pdf, exclude_ext):
    try:
        status = ingest_documents_from_directories(
            ["internal_data", "output"],
            chunk_size=chunk_size,
            overlap=overlap,
            include_pdf=include_pdf,
            exclude_ext=exclude_ext
        )
        return status or "✅ Ingestion completed successfully."
    except Exception as e:
        return f"❌ Ingestion failed: {str(e)}"

# === Tab 1: Ask Questions ===
tab1 = gr.Interface(
    fn=ask_and_debug,
    inputs=[
        gr.Textbox(label="Ask a question", lines=3),
        gr.Dropdown(["semantic", "keyword", "hybrid", "full"], label="Search Mode", value="semantic")
    ],
    outputs=[
        gr.Textbox(label="LLM Answer", lines=10),
        gr.Textbox(label="Debug Info", lines=4)
    ],
    title="📊 Local Competitive Intelligence Chat",
    description="Choose a search mode and ask your question about cybersecurity competitors or documents."
)

# === Tab 2: Trigger Ingestion ===
tab2 = gr.Interface(
    fn=trigger_ingestion,
    inputs=[
        gr.Slider(minimum=128, maximum=1024, step=64, value=512, label="Chunk Size"),
        gr.Slider(minimum=0, maximum=512, step=32, value=64, label="Chunk Overlap"),
        gr.Checkbox(label="Include PDFs"),
        gr.Textbox(label="Exclude Extensions (pipe-delimited, e.g. md|docx)")
    ],
    outputs=gr.Textbox(label="Ingestion Status", lines=4),
    title="📥 Ingest Documents",
    description="Trigger ingestion of internal_data and output folders using custom settings."
)

# === Launch Interface with Tabs ===
iface = gr.TabbedInterface([tab1, tab2])

if __name__ == "__main__":
    iface.launch()
