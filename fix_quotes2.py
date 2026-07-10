import os, ast

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

# Read raw bytes at line 732
with open(path, "rb") as f:
    raw_lines = f.readlines()

line732 = raw_lines[731]
print("Line 732 raw:", line732)

# Rewrite entire file replacing smart quotes
with open(path, "rb") as f:
    raw = f.read()

# U+2019 (right single quote) = E2 80 99 in UTF-8
# U+2018 (left single quote)  = E2 80 98 in UTF-8
fixed_raw = raw.replace(b"\xe2\x80\x99", b"'").replace(b"\xe2\x80\x98", b"'")
fixed_raw = fixed_raw.replace(b"\xe2\x80\x9c", b'"').replace(b"\xe2\x80\x9d", b'"')

changes = len(raw) - len(fixed_raw)
with open(path, "wb") as f:
    f.write(fixed_raw)
print(f"Rewrote file, byte diff = {changes} (0 means no curly quotes were present)")

# Now verify it parses
try:
    ast.parse(open(path, encoding="utf-8").read())
    print("Syntax OK!")
except SyntaxError as e:
    print(f"Still broken: {e}")
