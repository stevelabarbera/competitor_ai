from pathlib import Path
import subprocess

# Path to your test context file
TEST_CONTEXT_FILE = Path("test_context.txt")

# Model name
MODEL_NAME = "llama3:8b"  # Change to your preferred model

def query_ollama(prompt: str, model: str) -> str:
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def main():
    try:
        context = TEST_CONTEXT_FILE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Failed to read context: {e}")
        return

    question = "Compare companies with attack surface management offerings."

    prompt = f"""
You are a competitive intelligence assistant specializing in cybersecurity vendors. You have access to internal company documents and competitor analysis.

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
    print("🧪 Sending manual prompt to model...\n")
    response = query_ollama(prompt, MODEL_NAME)
    print("\n💬 Response:\n")
    print(response)

if __name__ == "__main__":
    main()
