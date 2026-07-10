import os, re, glob

base = os.path.dirname(os.path.abspath(__file__))

def resolve_keep_incoming(content):
    """Keep the INCOMING (>>>>>>>) side for every conflict block."""
    pattern = re.compile(
        r'<<<<<<< .*?\n(.*?)=======(.*?)>>>>>>> .*?\n',
        re.DOTALL
    )
    def replace(m):
        incoming = m.group(2)
        if incoming.startswith('\n'):
            incoming = incoming[1:]
        return incoming
    return re.subn(pattern, replace, content)

total_fixed = 0
for py_file in glob.glob(os.path.join(base, "backend", "**", "*.py"), recursive=True):
    content = open(py_file, encoding="utf-8", errors="replace").read()
    if "<<<<<<<" not in content:
        continue
    fixed, count = resolve_keep_incoming(content)
    open(py_file, "w", encoding="utf-8").write(fixed)
    rel = os.path.relpath(py_file, base)
    print(f"Resolved {count} conflicts in {rel}")
    total_fixed += count

print(f"\nTotal conflicts resolved: {total_fixed}")
