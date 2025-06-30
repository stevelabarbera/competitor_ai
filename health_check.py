# health_check.py
from search_engine import search_semantic, search_keyword

def check_semantic():
    print("Checking Semantic Search...")
    try:
        hits = search_semantic("test", n_results=2)
        if not hits:
            print("❌ Semantic search returned NO results. Is ChromaDB populated?")
            return False
        print(f"✅ Semantic search OK. Got {len(hits)} results.")
    except Exception as e:
        print(f"❌ Semantic search raised error: {e}")
        return False
    return True

def check_keyword():
    print("Checking Keyword Search...")
    try:
        hits = search_keyword("test", n_results=2)
        if not hits:
            print("❌ Keyword search returned NO results. Is Whoosh index built?")
            return False
        print(f"✅ Keyword search OK. Got {len(hits)} results.")
    except Exception as e:
        print(f"❌ Keyword search raised error: {e}")
        return False
    return True


def main():
    print("=== COMPETITOR_AI SYSTEM HEALTH CHECK ===")
    all_ok = True
    if not check_semantic():
        all_ok = False
    if not check_keyword():
        all_ok = False
    print("=========================================")
    if all_ok:
        print("✅ SYSTEM HEALTH: ALL SYSTEMS GO.")
    else:
        print("❌ SYSTEM HEALTH: ISSUES FOUND.")

if __name__ == "__main__":
    main()
