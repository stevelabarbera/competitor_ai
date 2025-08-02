import os
import ast

project_root = "/Users/stevelabarbera/Documents/GitHub/competitor_ai"  # Replace with your repo root


def find_callable_classes(root_dir):
    callables = []
    missing_instantiations = []

    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(subdir, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()
                        tree = aHe st.parse(source, filename=path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                for item in node.body:
                                    if isinstance(item, ast.FunctionDef) and item.name == "__call__":
                                        callables.append((node.name, path))
                            if isinstance(node, ast.Assign):
                                if hasattr(node.value, 'elts'):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Name):
                                            missing_instantiations.append((elt.id, path))
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    return callables, missing_instantiations


if __name__ == "__main__":
    callables, possibly_missing = find_callable_classes(project_root)

    print("\n📦 Callable Classes (have `__call__` defined):")
    for cls, file in callables:
        print(f"  - {cls} in {file}")

    print("\n⚠️  Classes possibly used without instantiation:")
    for cls, file in possibly_missing:
        print(f"  - {cls} in {file} (check if this is used as a class instead of an instance)")
