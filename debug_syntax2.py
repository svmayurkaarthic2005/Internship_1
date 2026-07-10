import os, tokenize, io

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

# Tokenize to find exactly where the error is
with open(path, "rb") as f:
    content = f.read()

# Try compiling and get exact error
import py_compile, sys
try:
    compile(content, path, "exec")
    print("Compiles OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    print(f"Text: {e.text!r}")
    # Show surrounding lines
    lines = content.split(b"\n")
    start = max(0, e.lineno - 5)
    end = min(len(lines), e.lineno + 3)
    for i in range(start, end):
        marker = " <-- ERROR" if i == e.lineno - 1 else ""
        print(f"{i+1:4d}: {lines[i]!r}{marker}")
