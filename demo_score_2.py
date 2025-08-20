# Run: python demo_preset_ui_scored.py
# Requires: pip install gradio==4.* (or latest)

from pathlib import Path
import subprocess
import gradio as gr
from datetime import datetime
import re
from itertools import chain
import json

# -----------------------------
# Config
# -----------------------------
DEFAULT_CONTEXT = Path("test_context.txt")  # or "full_context.txt"
DEFAULT_MODEL = "llama3:8b"

# Model list file (one per line). Lines starting with # are ignored.
MODEL_LIST_FILE = Path("models.txt")

TIMEOUT_SEC = 180            # safe default
Q1_TIMEOUT_SEC = 240         # Q1 tends to be longest
PREWARM_TIMEOUT_SEC = 30
MAX_CONTEXT_CHARS = 120_000  # cap very large files

PRESET_QUESTIONS = [
    "Build a concise battlecard comparing Tenable vs Shodan and Rapid7. Include strengths/weaknesses and cite sources.",
    "List any competitive information about Censys related to attack surface management. Cite sources.",
    "Summarize Tenable ASM differentiators mentioned in the context. Cite sources.",
    "What pricing/license insights are mentioned for any vendor? Keep it factual and cite sources.",
    "What product capabilities or features are highlighted for any vendor? Cite sources."
]

STRICT_PROMPT = """You are a competitive intelligence assistant specializing in cybersecurity vendors.
You MUST follow these rules:
1) USE ONLY the content in the context block below. Do NOT use outside knowledge.
2) EVERY concrete claim must include a citation like [Source_Name] that appears verbatim in the context.
3) If the context doesn’t contain the answer, reply exactly: "This information is not available in the current internal documents."
4) Do not speculate. Prefer precision over coverage. If unsure, say it’s not available.
5) Keep responses concise and structured for executives (bullets or a tight table).

--- START OF INTERNAL CONTEXT ---
{context}
--- END OF INTERNAL CONTEXT ---

QUESTION: {question}

Provide the ANSWER (based ONLY on the context above), with citations inline:
"""

# Optional file-backed demo answers (for fully scripted demos)
JSON_ANSWERS = Path("demo_answers.json")  # keys: answer1..answer5
TXT_ANSWERS = Path("demo_answers.txt")    # "Answer 1:" ... "Answer 5:" sections

# -----------------------------
# Helpers
# -----------------------------
def load_model_list():
    """Load models from models.txt; ignore blanks/#comments; fallback to [DEFAULT_MODEL]."""
    try:
        raw = MODEL_LIST_FILE.read_text(encoding="utf-8").splitlines()
        models = [ln.strip() for ln in raw if ln.strip() and not ln.strip().startswith("#")]
        return models if models else [DEFAULT_MODEL]
    except Exception:
        return [DEFAULT_MODEL]

def reload_models_ui():
    """Update dropdown choices and default selection."""
    choices = load_model_list()
    default_val = DEFAULT_MODEL if DEFAULT_MODEL in choices else choices[0]
    return gr.update(choices=choices, value=default_val)

def _parse_txt_answers(text: str):
    lines = text.replace("\r\n", "\n").split("\n")
    anchors = [f"Answer {i}:" for i in range(1, 6)]
    idx = {}
    for i, line in enumerate(lines):
        for a in anchors:
            if line.strip().lower().startswith(a.lower()):
                idx[a] = i
    answers = [""] * 5
    for i in range(5):
        a = f"Answer {i+1}:"
        if a in idx:
            start = idx[a] + 1
            following = [idx[f"Answer {j}:"] for j in range(i+2, 6) if f"Answer {j}:" in idx]
            end = min(following) if following else len(lines)
            answers[i] = "\n".join(lines[start:end]).strip()
    return answers

def load_file_backed_answers():
    if JSON_ANSWERS.exists():
        try:
            data = json.loads(JSON_ANSWERS.read_text(encoding="utf-8"))
            return [data.get(f"answer{i}", "") for i in range(1, 6)]
        except Exception as e:
            return [f"[Error reading {JSON_ANSWERS}: {e}]"] + [""]*4
    if TXT_ANSWERS.exists():
        try:
            return _parse_txt_answers(TXT_ANSWERS.read_text(encoding="utf-8"))
        except Exception as e:
            return [f"[Error reading {TXT_ANSWERS}: {e}]"] + [""]*4
    return ["", "", "", "", ""]

def read_context(path_str: str):
    path = Path(path_str.strip() or DEFAULT_CONTEXT)
    text = path.read_text(encoding="utf-8")
    if len(text) > MAX_CONTEXT_CHARS:
        head = text[: MAX_CONTEXT_CHARS // 2]
        tail = text[-MAX_CONTEXT_CHARS // 2 :]
        text = head + "\n...\n" + tail
    return text

def prewarm_model(model: str):
    try:
        subprocess.run(
            ["ollama", "run", model],
            input="OK",
            capture_output=True,
            text=True,
            timeout=PREWARM_TIMEOUT_SEC
        )
    except Exception:
        pass

def query_ollama_with_retry(prompt: str, model: str, timeout_sec: int, retries: int = 1) -> str:
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                ["ollama", "run", model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if result.returncode != 0:
                return f"❌ Model error (exit {result.returncode}): {err or '[no stderr]'}"
            return out if out else (f"⚠️ Empty model output. Stderr: {err}" if err else "⚠️ Empty model output.")
        except subprocess.TimeoutExpired:
            if attempt < retries:
                continue
            return f"❌ Timed out after {timeout_sec}s."
        except FileNotFoundError:
            return "❌ Ollama CLI not found. Is Ollama installed and on PATH?"

# -----------------------------
# Auto-scoring (lightweight)
# -----------------------------
CITATION_RE = re.compile(r"\[[^\[\]\n]{2,50}\]")
MONEY_RE = re.compile(r"(\$|USD)\s?\d[\d,]*(\.\d+)?")
PCT_RE = re.compile(r"\d{1,3}%")
THEMEPARK_RE = re.compile(r"theme\s*park", re.I)

def has_all_entities(answer: str, qnum: int) -> bool:
    if qnum != 1:
        return True
    want = ["Tenable", "Shodan", "Rapid7"]
    return all(w.lower() in (answer or "").lower() for w in want)

def is_correct_shape(answer: str, qnum: int) -> bool:
    if qnum == 1:
        a = answer or ""
        return ("|" in a and "---" in a) or ("- " in a) or ("•" in a)
    return True

def count_citations(answer: str) -> int:
    return len(CITATION_RE.findall(answer or ""))

def flags_for_answer(answer: str, qnum: int):
    flags = []
    a = answer or ""
    if "This information is not available in the current internal documents." in a:
        return flags
    if THEMEPARK_RE.search(a) and count_citations(a) == 0:
        flags.append(("F1", "Unsupported sensational claim (no source)."))
    if "[" in a and "]" in a and "http" not in a and count_citations(a) == 0:
        flags.append(("F2", "Citation brackets present but no valid source tokens found."))
    if (MONEY_RE.search(a) or PCT_RE.search(a)) and count_citations(a) == 0:
        flags.append(("F5", "Numbers present without any citations."))
    if qnum == 1 and not has_all_entities(a, qnum):
        flags.append(("COV", "Missing one or more vendors (Tenable/Shodan/Rapid7)."))
    return flags

def auto_score_answer(answer: str, qnum: int) -> str:
    a = 0
    if is_correct_shape(answer, qnum): a += 10
    if has_all_entities(answer, qnum): a += 10

    b = 0
    ccount = count_citations(answer)
    if ccount >= 1: b += 10
    if ccount >= 2: b += 7
    if ccount >= 3: b += 5
    if "This information is not available in the current internal documents." in (answer or ""):
        b += 3

    c = min(20, ccount * 5)
    d = 10 if ("This information is not available in the current internal documents." in (answer or "") or ccount >= 1) else 0

    e = 0
    atext = answer or ""
    if MONEY_RE.search(atext) or PCT_RE.search(atext): e += 5
    if ("- " in atext) or ("•" in atext) or ("|" in atext and "---" in atext): e += 5
    if len(atext.strip()) >= 200: e += 5

    f = 10

    raw = a + b + c + d + e + f

    fl = flags_for_answer(answer, qnum)
    deductions = 0
    for code, _ in fl:
        if code == "F1": deductions += 15
        elif code in ("F2", "F3"): deductions += 10
        elif code == "F4": deductions += 5
        elif code == "F5": deductions += 10
        elif code == "COV": deductions += 10

    total = max(0, raw - deductions)
    label = "PASS" if total >= 75 and not any(c == "F1" for c, _ in fl) else ("REVIEW" if total >= 60 else "FAIL")
    flag_str = "; ".join([f"{c}" for c, _ in fl]) or "—"
    return f"Score: {total}/100  →  {label}\nFlags: {flag_str}"

# -----------------------------
# Batch runner (with per-question enable)
# -----------------------------
def run_batch(model, context_file, answer_source,
              q1, q2, q3, q4, q5,
              e1, e2, e3, e4, e5,           # enable checkboxes
              prev_a1, prev_a2, prev_a3, prev_a4, prev_a5,
              prev_s1, prev_s2, prev_s3, prev_s4, prev_s5):
    """
    Only run the questions where the corresponding enable checkbox is True.
    Unchecked items will keep their previous answers/scores.
    """
    enabled = [e1, e2, e3, e4, e5]
    questions = [q1, q2, q3, q4, q5]
    prev_answers = [prev_a1, prev_a2, prev_a3, prev_a4, prev_a5]
    prev_scores  = [prev_s1, prev_s2, prev_s3, prev_s4, prev_s5]
    outs = list(prev_answers)  # start from previous; overwrite where enabled

    # Load context once (only if any enabled and using Ollama)
    context = None
    if any(enabled) and answer_source == "Ollama (context-backed)":
        try:
            context = read_context(context_file)
        except Exception as e:
            err = f"❌ Failed to read context file: {context_file} — {e}"
            # return previous answers + previous scores interleaved
            return list(chain.from_iterable(zip(prev_answers, prev_scores)))

    # Compute new answers for enabled indices
    if answer_source == "File-backed (scripted demo)":
        file_answers = load_file_backed_answers()
        for idx in range(5):
            if enabled[idx]:
                outs[idx] = file_answers[idx]
    else:
        model_name = (model or DEFAULT_MODEL).strip()
        for idx in range(5):
            if not enabled[idx]:
                continue
            q_clean = (questions[idx] or "").strip()
            if not q_clean:
                outs[idx] = "⚠️ No question provided."
                continue
            prompt = STRICT_PROMPT.format(context=context, question=q_clean)
            per_q_timeout = Q1_TIMEOUT_SEC if idx == 0 else TIMEOUT_SEC
            outs[idx] = query_ollama_with_retry(prompt, model_name, per_q_timeout, retries=1)

    # Scores: recompute for enabled, keep previous for disabled
    scores = list(prev_scores)
    for idx in range(5):
        if enabled[idx]:
            scores[idx] = auto_score_answer(outs[idx], idx + 1)

    # Interleave to match outputs wiring: a1,s1,a2,s2,...
    return list(chain.from_iterable(zip(outs, scores)))

# -----------------------------
# Export (supports both call styles)
# -----------------------------
def export_markdown(*args):
    """
    Accepts EITHER:
      - (qs_list, ans_list, scores_list)
      - (q1..q5, a1..a5, s1..s5)  -> 15 args
    """
    if len(args) == 3 and all(isinstance(x, list) for x in args):
        qs, ans, scs = args
    elif len(args) == 15:
        qs  = [args[i] for i in range(0, 5)]
        ans = [args[i] for i in range(5, 10)]
        scs = [args[i] for i in range(10, 15)]
    else:
        return f"❌ export_markdown expected (qs,ans,scs) or 15 flat args; got {len(args)} args."

    def _pad5(x): return (x + [""]*5)[:5]
    qs, ans, scs = _pad5(qs), _pad5(ans), _pad5(scs)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# CI Demo Q&A Export\n\n_Exported: {ts}_\n"]
    for i in range(5):
        q = (qs[i] or "").strip() or "*[empty]*"
        a = (ans[i] or "").strip() or "*[empty]*"
        s = (scs[i] or "").strip() or "Score: —"
        lines.append(f"## Question {i+1}\n{q}\n")
        lines.append(f"**Answer {i+1}**\n\n{a}\n")
        lines.append(f"**Auto-Score**\n\n{s}\n")

    out = Path("demo_run_export.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    return f"✅ Exported to {out.resolve()}"

# -----------------------------
# UI
# -----------------------------
with gr.Blocks(title="🎯 CI Demo Presets (Scored)") as demo:
    gr.Markdown("## 🎯 Competitive Intelligence — Demo Presets (Scored)\n"
                "Pick a model from `models.txt`, select which questions to run, and generate answers from your local context or scripted file.\n"
                "Each answer is auto-scored with lightweight rubric checks and flags.")

    with gr.Row():
        model = gr.Dropdown(
            choices=load_model_list(),
            value=(DEFAULT_MODEL if DEFAULT_MODEL in load_model_list() else load_model_list()[0]),
            label="Ollama model",
            info="Loaded from models.txt (one per line). You can also type a custom value.",
            allow_custom_value=True,
        )
        reload_models_btn = gr.Button("🔄 Reload Models")
        context_file = gr.Textbox(value=str(DEFAULT_CONTEXT), label="Context file path", info="test_context.txt or full_context.txt")
        answer_source = gr.Dropdown(
            choices=["Ollama (context-backed)", "File-backed (scripted demo)"],
            value="Ollama (context-backed)", label="Answer source"
        )

    gr.Markdown("### Preset Questions (edit as needed) + Select which to run")
    with gr.Row():
        q1 = gr.Textbox(value=PRESET_QUESTIONS[0], lines=2, label="Question 1")
        e1 = gr.Checkbox(value=True, label="Run Q1")
    with gr.Row():
        q2 = gr.Textbox(value=PRESET_QUESTIONS[1], lines=2, label="Question 2")
        e2 = gr.Checkbox(value=True, label="Run Q2")
    with gr.Row():
        q3 = gr.Textbox(value=PRESET_QUESTIONS[2], lines=2, label="Question 3")
        e3 = gr.Checkbox(value=True, label="Run Q3")
    with gr.Row():
        q4 = gr.Textbox(value=PRESET_QUESTIONS[3], lines=2, label="Question 4")
        e4 = gr.Checkbox(value=True, label="Run Q4")
    with gr.Row():
        q5 = gr.Textbox(value=PRESET_QUESTIONS[4], lines=2, label="Question 5")
        e5 = gr.Checkbox(value=True, label="Run Q5")

    # Master Select All
    with gr.Row():
        run_all = gr.Checkbox(value=True, label="Run All (toggle)")
        def set_all(b):
            return [gr.update(value=b) for _ in range(5)]
        run_all.change(set_all, inputs=[run_all], outputs=[e1, e2, e3, e4, e5])

    with gr.Row():
        run_btn = gr.Button("🚀 Run Selected", variant="primary")
        reload_btn = gr.Button("🔁 Reload Context")
        export_btn = gr.Button("📝 Export Q&A to Markdown")
        export_status = gr.Markdown("")

    gr.Markdown("### Responses + Scores")
    a1 = gr.Textbox(label="Answer 1", lines=10)
    s1 = gr.Markdown("")
    a2 = gr.Textbox(label="Answer 2", lines=10)
    s2 = gr.Markdown("")
    a3 = gr.Textbox(label="Answer 3", lines=10)
    s3 = gr.Markdown("")
    a4 = gr.Textbox(label="Answer 4", lines=10)
    s4 = gr.Markdown("")
    a5 = gr.Textbox(label="Answer 5", lines=10)
    s5 = gr.Markdown("")

    # Run selected questions; keep others as-is
    run_btn.click(
        fn=run_batch,
        inputs=[
            model, context_file, answer_source,
            q1, q2, q3, q4, q5,
            e1, e2, e3, e4, e5,
            a1, a2, a3, a4, a5,
            s1, s2, s3, s4, s5
        ],
        outputs=[a1, s1, a2, s2, a3, s3, a4, s4, a5, s5],
    )

    # Reload models dropdown
    reload_models_btn.click(
        fn=reload_models_ui,
        inputs=[],
        outputs=[model],
    )

    # Reload context sanity check
    def reload_context_ui(context_file):
        try:
            _ = read_context(context_file)
            return "✅ Context reloaded."
        except Exception as e:
            return f"❌ Reload failed: {e}"

    reload_btn.click(
        fn=reload_context_ui,
        inputs=[context_file],
        outputs=[export_status],
    )

    # Export (flat inputs)
    export_btn.click(
        fn=export_markdown,
        inputs=[q1, q2, q3, q4, q5, a1, a2, a3, a4, a5, s1, s2, s3, s4, s5],
        outputs=[export_status],
    )

if __name__ == "__main__":
    prewarm_model(DEFAULT_MODEL)  # avoid first-call latency
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)
