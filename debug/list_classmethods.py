import ast

def list_methods_and_classes_from_file(filepath):
    """
    Parses a Python file and lists all class names and method names.
    """
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())

    print(f"--- Classes and Methods in {filepath} ---")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            print(f"Class: {node.name}")
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    print(f"  Method: {item.name}")
        elif isinstance(node, ast.FunctionDef):
            # For standalone functions at the module level
            print(f"Function: {node.name}")

# Example Usage:
# Create a dummy Python file for demonstration
dummy_code = """
class ExampleClass:
    def __init__(self):
        pass
    def first_method(self):
        pass
    def second_method(self):
        pass

def global_function():
    pass
"""
#with open("temp_script.py", "w") as f:
#   f.write(dummy_code)
 file_name = '--file_name' in sys.argv
    
    # Check if custom collection name provided
    if '--file_name' in sys.argv:
        try:
            idx = sys.argv.index('--file_name')
            file_name = sys.argv[idx + 1]
        except (IndexError, ValueError):
            print("❌ Invalid --file_name argument")
            return False
    
list_methods_and_classes_from_file("temp_script.py")