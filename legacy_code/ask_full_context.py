import ollama

def main():
    with open("full_context.txt", "r") as f:
        full_context = f.read()

    # Truncate to first 12,000 characters (roughly 3K tokens)
    truncated_context = full_context[:12000]

    print("❓ Enter your question: ", end="")
    question = input()

    prompt = f"""You are an expert assistant answering based on the following internal company and competitor documents:

{truncated_context}

Now answer the question clearly and directly:
{question}
"""

    print("🚀 Running Ollama...")
    response = ollama.chat(model='llama3', messages=[{"role": "user", "content": prompt}])

    print("\n🧠 Answer:\n")
    print(response['message']['content'])

if __name__ == "__main__":
    main()
