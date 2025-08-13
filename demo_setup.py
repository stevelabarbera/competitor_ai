# demo_preset_ui.py
# Run: python demo_preset_ui.py

from pathlib import Path
import subprocess
import gradio as gr

DEFAULT_CONTEXT = Path("test_context.txt")  # or "full_context.txt"
DEFAULT_MODEL = "llama3:8b"#all-manylm:latest, llama3:instruct, phi3:minic ,llama3:latest,mistral:7b,phi-4, gemma2(9b or 27b),deep seek 1.5b# 
#aya23,llama3.23b,llama 3.1q8,mistral small 2501, qwen2.5,0.5b,1.5b,qwen2.5 3b,dolphin 3.8b,hermes llama 3.2 3b,nous hermes3.8b,Qwen2.5 14b,celeste 12bq8
PRESET_QUESTIONS = [
    "Build a concise battlecard comparing Tenable vs Shodan and Rapid7. Include strengths/weaknesses and cite sources.",
    "List any competitive information about Censys related to attack surface management. Cite sources.",
    "Summarize Tenable ASM differentiators mentioned in the context. Cite sources.",
    "What pricing/license insights are mentioned for any vendor? Keep it factual and cite sources.",
    "What product capabilities or features are highlighted for any vendor? Cite sources."
]

PROMPT_TEMPLATE = """You are a competitive intelligence assistant specializing in cybersecurity vendors. You have access to internal company documents and competitor analysis.

CRITICAL INSTRUCTIONS:
1. ONLY use information from the provided context below
2. Do NOT use your general knowledge about companies or products
3. If the context doesn't contain the answer, respond: "This information is not available in the current internal documents."
4. Always cite your sources using the format [source_name]
5. Be specific and factual - avoid speculation
6. Focus on competitive intelligence insights, pricing, and product comparisons

--- START OF INTERNAL CONTEXT ---
{context}
--- END OF INTERNAL CONTEXT ---

QUESTION: {question}

ANSWER (based only on the context above):
"""

def query_ollama(prompt: str, model: str) -> str:
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def run_demo(model, context_file, q1, q2, q3, q4, q5):
    path = Path(context_file.strip() or DEFAULT_CONTEXT)
    try:
        context = path.read_text(encoding="utf-8")
    except Exception as e:
        err = f"❌ Failed to read context file: {path} — {e}"
        return [err, err, err, err, err]

    questions = [q1, q2, q3, q4, q5]
    outs = []
    for q in questions:
        q_clean = (q or "").strip()
        if not q_clean:
            outs.append("⚠️ No question provided.")
            continue
        prompt = PROMPT_TEMPLATE.format(context=context, question=q_clean)
        outs.append(query_ollama(prompt, model.strip() or DEFAULT_MODEL))
    return outs

with gr.Blocks(title="🎯 CI Demo Presets") as demo:
    gr.Markdown("## 🎯 Competitive Intelligence — Demo Presets")
    gr.Markdown("Click **Run Demo** to ask multiple prewritten questions against your local context file.")

    with gr.Row():
        model = gr.Textbox(value=DEFAULT_MODEL, label="Ollama model", info="e.g. llama3:8b or command-r-plus:latest")
        context_file = gr.Textbox(value=str(DEFAULT_CONTEXT), label="Context file path", info="test_context.txt or full_context.txt")

    gr.Markdown("### Preset Questions (edit as needed)")
    with gr.Row():
        q1 = gr.Textbox(value=PRESET_QUESTIONS[0], lines=2, label="Question 1")
    with gr.Row():
        q2 = gr.Textbox(value=PRESET_QUESTIONS[1], lines=2, label="Question 2")
    with gr.Row():
        q3 = gr.Textbox(value=PRESET_QUESTIONS[2], lines=2, label="Question 3")
    with gr.Row():
        q4 = gr.Textbox(value=PRESET_QUESTIONS[3], lines=2, label="Question 4")
    with gr.Row():
        q5 = gr.Textbox(value=PRESET_QUESTIONS[4], lines=2, label="Question 5")

    run_btn = gr.Button("🚀 Run Demo", variant="primary")

    gr.Markdown("### Responses")
    with gr.Row():
        a1 = gr.Textbox(label="Answer 1", lines=10)
    with gr.Row():
        a2 = gr.Textbox(label="Answer 2", lines=10)
    with gr.Row():
        a3 = gr.Textbox(label="Answer 3", lines=10)
    with gr.Row():
        a4 = gr.Textbox(label="Answer 4", lines=10)
    with gr.Row():
        a5 = gr.Textbox(label="Answer 5", lines=10)

    run_btn.click(
        fn=run_demo,
        inputs=[model, context_file, q1, q2, q3, q4, q5],
        outputs=[a1, a2, a3, a4, a5]
    )

if __name__ == "__main__":
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)
