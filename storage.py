"""Saves and loads all your data in the data/ folder (kept private by .gitignore)."""
import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "tracker.json"
RESUME_FILE = DATA_DIR / "resume.txt"
HISTORY_FILE = DATA_DIR / "chat_history.json"
UPLOADS_DIR = DATA_DIR / "uploads"


def _default():
    return {"interests": [], "applications": [], "reminders": [], "memories": [], "next_id": 1}


def load() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        return _default()
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for key, value in _default().items():
        data.setdefault(key, value)
    return data


def _safe_write(path: Path, obj) -> None:
    # Write to a temp file first, then swap it in, so a crash can't corrupt your data
    DATA_DIR.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    tmp.replace(path)


def save(data: dict) -> None:
    _safe_write(DATA_FILE, data)


def new_id(data: dict) -> int:
    i = data["next_id"]
    data["next_id"] += 1
    return i


def today() -> str:
    return date.today().isoformat()


# ---------- Chat history (so the agent remembers past conversations) ----------

def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: list) -> None:
    _safe_write(HISTORY_FILE, history)


def clear_history() -> None:
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
