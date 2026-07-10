import os

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

with open(path, "rb") as f:
    raw = f.read()

# Find line number of position 3672
lines_up_to = raw[:3672].count(b"\n")
print(f"Arrow chars are around line {lines_up_to + 1}")

# Show that line
all_lines = raw.split(b"\n")
for i in range(lines_up_to - 2, lines_up_to + 5):
    print(f"{i+1:4d}: {all_lines[i]!r}")
