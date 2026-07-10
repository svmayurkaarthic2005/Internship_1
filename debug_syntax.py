import os, tokenize, io

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

with open(path, "rb") as f:
    raw_lines = f.readlines()

# Print lines 720-740 with repr
for i in range(719, 740):
    print(f"{i+1:4d}: {raw_lines[i]!r}")
