# reset_hard_whoosh.py
import shutil
from pathlib import Path

WHOOSH_DIR = Path("./whoosh_index")

if WHOOSH_DIR.exists():
    print(f"🧨 Nuking old Whoosh index at: {WHOOSH_DIR}")
    shutil.rmtree(WHOOSH_DIR)

# Optionally recreate the directory
WHOOSH_DIR.mkdir(parents=True, exist_ok=True)

print(f"✅ Whoosh index directory reset. Rebuild it using your build_whoosh_index.py script.")
