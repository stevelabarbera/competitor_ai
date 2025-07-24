# reset_hard_whoosh.py
import shutil
from pathlib import Path

paths_to_reset = {
    "Whoosh keyword index": Path("./whoosh_index"),
    "Company index": Path("./company_index"),
    "ChromaDB vector store": Path("./chroma_db"),
}

for name, path in paths_to_reset.items():
    if path.exists():
        print(f"🧨 Nuking {name} at: {path}")
        shutil.rmtree(path)
    else:
        print(f"ℹ️  {name} not found at: {path}")
    # Optional: recreate empty directories if needed
    path.mkdir(parents=True, exist_ok=True)

print("✅ All major local indexes have been reset. Rebuild them as needed.")
