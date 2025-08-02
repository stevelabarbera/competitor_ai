from search_engine import ask

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ask questions using local RAG pipeline")
    parser.add_argument("question", type=str, help="The question to ask")
    parser.add_argument("--mode", type=str, default="semantic",
                        choices=["semantic", "keyword", "hybrid", "full"],
                        help="Search mode to use")
    args = parser.parse_args()

    answer = ask(args.question, mode=args.mode)
    print(f"🧠 Answer:\n{answer}")

if __name__ == "__main__":
    main()
