import ast
import sys
from pathlib import Path
import argparse

sys.setrecursionlimit(3000)  # Raise recursion limit cautiously

def extract_functions(filepath, verbosity, max_depth=5):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except Exception as e:
            return [], str(e)

    functions = []

    def visit_node(node, parent_class=None, depth=0):
        if depth > max_depth:
            return  # Prevent infinite loops

        if isinstance(node, ast.FunctionDef):
            prefix = f"{parent_class + '.' if parent_class else ''}{node.name}"
            if verbosity == "low":
                functions.append(prefix)
            elif verbosity == "normal":
                functions.append(f"{prefix} (line {node.lineno})")
            elif verbosity == "fine":
                args = [arg.arg for arg in node.args.args]
                functions.append(f"{prefix}({', '.join(args)}) → line {node.lineno}")

        elif isinstance(node, ast.ClassDef):
            for body_item in node.body:
                visit_node(body_item, parent_class=node.name, depth=depth + 1)

        else:
            for child in ast.iter_child_nodes(node):
                visit_node(child, parent_class, depth)

    visit_node(tree)
    return functions, None

def should_ignore(path_parts, ignore_dirs):
    return any(ignored in path_parts for ignored in ignore_dirs)

def scan_directory(root, ignore_dirs, verbosity):
    results = {}
    errors = {}

    for filepath in Path(root).rglob("*.py"):
        if should_ignore(filepath.parts, ignore_dirs):
            continue

        funcs, err = extract_functions(filepath, verbosity)
        if err:
            errors[str(filepath)] = err
        elif funcs:
            results[str(filepath)] = funcs

    return results, errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Root directory to scan")
    parser.add_argument("--ignore", default="", help="Comma-separated folders to ignore")
    parser.add_argument("--verbosity", choices=["low", "normal", "fine"], default="normal")
    args = parser.parse_args()

    ignore_dirs = set(args.ignore.split(",")) if args.ignore else set()
    print(f"🔍 Scanning '{args.root}' with verbosity='{args.verbosity}'")
    results, errors = scan_directory(args.root, ignore_dirs, args.verbosity)

    for file, funcs in sorted(results.items()):
        print(f"\n📄 {Path(file).name}")
        for f in funcs:
            print(f"   - {f}")

    for file, err in errors.items():
        print(f"⚠️ Failed to parse {Path(file).name}: {err}")

if __name__ == "__main__":
    main()
