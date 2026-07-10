import os, ast, glob

base = os.path.dirname(os.path.abspath(__file__))

errors = []
ok = []
for py_file in glob.glob(os.path.join(base, "backend", "**", "*.py"), recursive=True):
    rel = os.path.relpath(py_file, base)
    try:
        content = open(py_file, encoding="utf-8", errors="replace").read()
        # Check for remaining conflict markers
        if "<<<<<<< " in content or ">>>>>>> " in content:
            errors.append((rel, "MERGE CONFLICT MARKERS REMAINING"))
            continue
        ast.parse(content)
        ok.append(rel)
    except SyntaxError as e:
        errors.append((rel, f"SyntaxError line {e.lineno}: {e.msg}"))

print(f"OK: {len(ok)} files")
if errors:
    print(f"\nERRORS ({len(errors)}):")
    for f, e in errors:
        print(f"  {f}: {e}")
else:
    print("All backend Python files are syntax-clean!")
