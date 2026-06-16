import ast

with open('d:/MapR1/backend/simulation/consequence_engine.py', 'r') as f:
    source = f.read()

tree = ast.parse(source)

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == '_inject_retaliation_motivations':
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                print(f"If statement at line {child.lineno}")
                for stmt in child.body:
                    print(f"  Body stmt: {type(stmt).__name__} at line {stmt.lineno}")
