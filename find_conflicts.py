import os

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

with open(path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

conflict_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("<<<<<<<") or stripped.startswith("=======") or stripped.startswith(">>>>>>>"):
        conflict_lines.append((i + 1, line.rstrip()))

print(f"Found {len(conflict_lines)} conflict marker lines:")
for lineno, text in conflict_lines:
    print(f"  Line {lineno}: {text!r}")
