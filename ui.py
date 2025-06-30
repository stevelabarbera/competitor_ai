import gradio as gr
import subprocess
from search_engine import ask

# === Tab 1: Ask a Question ===
def ask_and_debug(question, mode):
    answer = ask(question, mode=mode)
    return answer, f"✅ Answered using mode: {mode}"

with gr.Blocks(title="📊 Local Competitive Intelligence Chat") as iface:
    with gr.Tab("💬 Ask a Question"):
        with gr.Row():
            question_box = gr.Textbox(label="Question", lines=4, placeholder="Ask something about cybersecurity competitors...")
        mode_dropdown = gr.Dropdown(["semantic", "keyword", "hybrid", "full"], value="semantic", label="Search Mode")
        with gr.Row():
            answer_box = gr.Textbox(label="LLM Answer", lines=10)
            debug_box = gr.Textbox(label="Debug Info", lines=10)

        gr.Button("Ask").click(
            ask_and_debug,
            inputs=[question_box, mode_dropdown],
            outputs=[answer_box, debug_box]
        )

    # === Tab 2: Data Manager ===
    with gr.Tab("🗂️ Data Manager"):
        with gr.Row():
            pdf_toggle = gr.Checkbox(label="Include PDFs", value=True)
            limit_box = gr.Number(label="Limit documents (optional)", precision=0)
        with gr.Row():
            chunk_slider = gr.Slider(minimum=128, maximum=2048, step=64, value=512, label="Chunk Size")
            overlap_slider = gr.Slider(minimum=0, maximum=512, step=16, value=64, label="Chunk Overlap")
        output_log = gr.Textbox(label="Output Log", lines=10)

        def reset_and_ingest(pdf_toggle, chunk_size, overlap, limit):
            subprocess.run(["python3", "reset_hard.py"])

            cmd = [
                "python3", "ingest_internal_doc.py",
                "--chunk-size", str(chunk_size),
                "--overlap", str(overlap)
            ]
            if not pdf_toggle:
                cmd += ["--exclude-ext", "pdf"]
            if limit:
                cmd += ["--limit", str(int(limit))]

            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout or result.stderr or "✅ Done."
            return f"🔁 Reset + Ingest triggered...\n\n{output}"

        gr.Button("🔄 Reset & Reingest All").click(
            reset_and_ingest,
            inputs=[pdf_toggle, chunk_slider, overlap_slider, limit_box],
            outputs=output_log
        )

if __name__ == "__main__":
    iface.launch()
