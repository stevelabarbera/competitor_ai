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
TIMEOUT_SEC = 180            # was 90; safer default
Q1_TIMEOUT_SEC = 240         # Q1 tends to be longest
PREWARM_TIMEOUT_SEC = 30
MAX_CONTEXT_CHARS = 120_000  # cap very large files to avoid overlong generations

PRESET_QUESTIONS = [
    "Build a concise battlecard comparing Tenable vs Shodan and Rapid7. Include strengths/weaknesses and cite sources.",
    "List any competitive information about Censys related to attack surface management. Cite sources.",
    "Summarize Tenable ASM differentiators mentioned in the context. Cite sources.",
    "What pricing/license insights are mentioned for any vendor? Keep it factual and cite sources.",
    "What product capabilities or features are highlighted for any vendor? Cite sources."
]
#1) USE ONLY the content in the context block below. Do NOT use outside knowledge.


STRICT_PROMPT = """You are a competitive intelligence assistant specializing in cybersecurity vendors.
You MUST follow these rules:
1) Tried to prioritize the content in the context block below but try to include at least one additional data point from outside sources at your discretion.
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
    # Trim extremely large contexts to reduce latency/timeouts.
    if len(text) > MAX_CONTEXT_CHARS:
        head = text[: MAX_CONTEXT_CHARS // 2]
        tail = text[-MAX_CONTEXT_CHARS // 2 :]
        text = head + "\n...\n" + tail
    return text

def prewarm_model(model: str):
    """Warm up the model once to avoid first-call cold-start delays."""
    try:
        subprocess.run(
            ["ollama", "run", model],
            input="OK",
            capture_output=True,
            text=True,
            timeout=PREWARM_TIMEOUT_SEC
        )
    except Exception:
        # Non-fatal if prewarm fails.
        pass

def query_ollama_with_retry(prompt: str, model: str, timeout_sec: int, retries: int = 1) -> str:
    """Run Ollama with a timeout and a simple retry on TimeoutExpired."""
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
# Batch runner
# -----------------------------
def run_batch(model, context_file, q1, q2, q3, q4, q5, answer_source):
    # Load & trim context
    try:
        context = read_context(context_file)
    except Exception as e:
        err = f"❌ Failed to read context file: {context_file} — {e}"
        outs = [err]*5
        scores = [auto_score_answer(ans, i+1) for i, ans in enumerate(outs)]
        # Interleave to match outputs wiring: a1,s1,a2,s2,...
        return list(chain.from_iterable(zip(outs, scores)))

    questions = [q1, q2, q3, q4, q5]
    outs = []

    if answer_source == "File-backed (scripted demo)":
        outs = load_file_backed_answers()
    else:
        model_name = (model or DEFAULT_MODEL).strip()
        for idx, q in enumerate(questions):
            q_clean = (q or "").strip()
            if not q_clean:
                outs.append("⚠️ No question provided.")
                continue
            prompt = STRICT_PROMPT.format(context=context, question=q_clean)
            per_q_timeout = Q1_TIMEOUT_SEC if idx == 0 else TIMEOUT_SEC
            outs.append(query_ollama_with_retry(prompt, model_name, per_q_timeout, retries=1))

    # Normalize to exactly 5 answers
    outs = (outs + [""]*5)[:5]
    scores = [auto_score_answer(ans, idx+1) for idx, ans in enumerate(outs)]

    # Interleave to match outputs wiring: a1,s1,a2,s2,...
    return list(chain.from_iterable(zip(outs, scores)))

# -----------------------------
# Auto-scoring (lightweight, rubric-aligned)
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
    # Loose check: bullets or table-like for Q1
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
        return flags  # refusal is okay

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
                "Run 5 preset questions against a local context file via Ollama **or** use file-backed scripted answers.\n"
                "Each answer is auto-scored with lightweight rubric checks and flags.")

    with gr.Row():
        model = gr.Textbox(value=DEFAULT_MODEL, label="Ollama model", info="e.g. llama3:8b")
        context_file = gr.Textbox(value=str(DEFAULT_CONTEXT), label="Context file path", info="test_context.txt or full_context.txt")
        answer_source = gr.Dropdown(
            choices=["Ollama (context-backed)", "File-backed (scripted demo)"],
            value="Ollama (context-backed)", label="Answer source"
        )

    gr.Markdown("### Preset Questions (editable)")
    q1 = gr.Textbox(value=PRESET_QUESTIONS[0], lines=2, label="Question 1")
    q2 = gr.Textbox(value=PRESET_QUESTIONS[1], lines=2, label="Question 2")
    q3 = gr.Textbox(value=PRESET_QUESTIONS[2], lines=2, label="Question 3")
    q4 = gr.Textbox(value=PRESET_QUESTIONS[3], lines=2, label="Question 4")
    q5 = gr.Textbox(value=PRESET_QUESTIONS[4], lines=2, label="Question 5")

    with gr.Row():
        run_btn = gr.Button("🚀 Run Demo", variant="primary")
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

    run_btn.click(
        fn=run_batch,
        inputs=[model, context_file, q1, q2, q3, q4, q5, answer_source],
        outputs=[a1, s1, a2, s2, a3, s3, a4, s4, a5, s5],
    )

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

    export_btn.click(
        fn=export_markdown,
        inputs=[q1, q2, q3, q4, q5, a1, a2, a3, a4, a5, s1, s2, s3, s4, s5],
        outputs=[export_status],
    )

if __name__ == "__main__":
    # Prewarm once to avoid first-call latency/timeouts
    prewarm_model(DEFAULT_MODEL)
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)
