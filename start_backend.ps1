$env:PYTHONPATH = "c:\proj\nic_internship"
& "c:\proj\nic_internship\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
