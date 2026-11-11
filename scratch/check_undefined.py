import ast
import builtins

with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

# Collect all top-level defined names and imports
top_level_defs = set(dir(builtins))
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        top_level_defs.add(node.name)
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                top_level_defs.add(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        top_level_defs.add(elt.id)
    elif isinstance(node, ast.Import):
        for alias in node.names:
            top_level_defs.add(alias.asname or alias.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            top_level_defs.add(alias.asname or alias.name)

# Now inspect handle_ai_voice_flow specifically
voice_flow_node = None
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'handle_ai_voice_flow':
        voice_flow_node = node
        break

if voice_flow_node:
    # Check all variables used inside handle_ai_voice_flow
    local_defs = set()
    for arg in voice_flow_node.args.args:
        local_defs.add(arg.arg)

    undefined = set()
    for child in ast.walk(voice_flow_node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_defs.add(child.name)
        elif isinstance(child, ast.Assign):
            for t in child.targets:
                if isinstance(t, ast.Name):
                    local_defs.add(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for elt in t.elts:
                        if isinstance(elt, ast.Name):
                            local_defs.add(elt.id)
        elif isinstance(child, ast.For):
            if isinstance(child.target, ast.Name):
                local_defs.add(child.target.id)
            elif isinstance(child.target, (ast.Tuple, ast.List)):
                for elt in child.target.elts:
                    if isinstance(elt, ast.Name):
                        local_defs.add(elt.id)
        elif isinstance(child, ast.ExceptHandler):
            if child.name:
                local_defs.add(child.name)
        elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            var_name = child.id
            if var_name not in top_level_defs and var_name not in local_defs:
                undefined.add((child.lineno, var_name))

    print(f"Undefined names in handle_ai_voice_flow: {sorted(undefined)}")
else:
    print("handle_ai_voice_flow not found")
