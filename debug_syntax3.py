import os

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "backend", "services", "postgres.py")

with open(path, "rb") as f:
    raw = f.read()

# Find the problem line
idx = raw.find(b"officer's jurisdiction")
if idx == -1:
    idx = raw.find(b"officer\xe2\x80\x99s")
    print("Found curly quote version")
else:
    print("Found plain apostrophe version")

# Show 30 bytes around it
print("Context bytes:", repr(raw[idx-5:idx+40]))

# Count \r\n vs \r vs \n
crlf = raw.count(b"\r\n")
cr_only = raw.count(b"\r") - crlf
lf_only = raw.count(b"\n") - crlf
print(f"CRLF: {crlf}, bare CR: {cr_only}, bare LF: {lf_only}")
