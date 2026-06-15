# storage.py – Simple JSON file persistence for session data

"""Provides load/save helpers for per‑session data.

Each session gets a JSON file under ``data/sessions/<session_id>.json``.
If the file does not exist we return an empty dict.
"""

import os
import json
from pathlib import Path

# Resolve the project root (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "data" / "sessions"

os.makedirs(SESSIONS_DIR, exist_ok=True)

def _session_path(session_id: str) -> Path:
    # Sanitize to avoid path traversal
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "_-")
    return SESSIONS_DIR / f"{safe_id}.json"

def load_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_session(session_id: str, data: dict) -> None:
    path = _session_path(session_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
