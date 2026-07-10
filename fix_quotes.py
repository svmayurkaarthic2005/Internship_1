import os

base = os.path.dirname(os.path.abspath(__file__))

files = [
    "backend/services/postgres.py",
    "backend/services/chatbot.py",
    "backend/services/rag.py",
    "backend/routers/chat.py",
]

for rel in files:
    path = os.path.join(base, rel)
    try:
        content = open(path, encoding="utf-8").read()
        fixed = content.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
        if fixed != content:
            open(path, "w", encoding="utf-8").write(fixed)
            n = content.count("\u2019") + content.count("\u2018") + content.count("\u201c") + content.count("\u201d")
            print(f"Fixed {n} curly quotes in {rel}")
        else:
            print(f"Clean: {rel}")
    except FileNotFoundError:
        print(f"Not found: {path}")
