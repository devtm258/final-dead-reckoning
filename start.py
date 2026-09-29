"""Run from any working directory after installing backend requirements."""
import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
print("Open http://127.0.0.1:8000 — Ctrl+C stops the server. Saved models remain on disk.",flush=True)
raise SystemExit(subprocess.call([sys.executable,"-m","uvicorn","server:app","--host","127.0.0.1","--port","8000","--workers","1"],cwd=root/"backend"))
