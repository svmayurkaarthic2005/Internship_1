import os

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

with open(path, "rb") as f:
    raw = f.read()

# Find all occurrences of the phrase
phrase = b"officer"
start = 0
occurrences = []
while True:
    idx = raw.find(phrase, start)
    if idx == -1:
        break
    occurrences.append(idx)
    start = idx + 1

print(f"Found {len(occurrences)} occurrences of 'officer'")
for idx in occurrences:
    ctx = raw[idx:idx+60]
    # Check for any non-ASCII bytes in vicinity
    suspect = any(b > 127 for b in raw[idx:idx+60])
    if suspect:
        print(f"  pos {idx}: NON-ASCII: {repr(ctx)}")

# Also look for any non-ASCII byte in the whole file
non_ascii_positions = [i for i, b in enumerate(raw) if b > 127]
print(f"\nTotal non-ASCII bytes: {len(non_ascii_positions)}")
if non_ascii_positions:
    for pos in non_ascii_positions[:20]:
        print(f"  pos {pos}: {repr(raw[pos-10:pos+20])}")
