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
1000w.1#69{ and the interpretation often is a recallis that with`461.16%'1000w.1#69{ and the interpretation often is a recallis that with`461.16%2tin {s}
'pi(->337:.312averageFirstCorrectResultp2tin {s}increase bmfRanking 4:1011 > o10 is None2baselineMetricsToCompeteAgainstWeCanMove12>(8
to do this I'll likely do you find directly so findingi10kLoss Renata++.1'with what riding'1b^'do it's minimizes the dice'10+10a)