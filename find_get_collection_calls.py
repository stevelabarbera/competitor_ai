import os
import re

# Directory to search
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # current dir

# Regex to catch .get_collection calls (even split across lines)
GET_COLLECTION_RE = re.compile(r'\.get_collection\s*\(')

def scan_files(root_dir):
    for root, _, files in os.walk(root_dir):
        for fname in files:
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                with open(fpath, encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for idx, line in enumerate(lines):
                        if GET_COLLECTION_RE.search(line):
                            # Print a little context (the line before and after)
                            print(f"\nFile: {fpath} (Line {idx+1})")
                            if idx > 0:
                                print("Prev:", lines[idx-1].strip())
                            print("Line:", line.strip())
                            if idx < len(lines)-1:
                                print("Next:", lines[idx+1].strip())

if __name__ == "__main__":
    print("Scanning for '.get_collection(' calls...")
    scan_files(ROOT_DIR)
    print("\nScan complete.")
