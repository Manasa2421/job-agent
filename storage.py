"""Saves and loads all your job-search data in data/tracker.json."""
import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "tracker.json"
RESUME_FILE = DATA_DIR / "resume.txt"


def _default():
    return {"interests": [], "applications": [], "reminders": [], "next_id": 1}


def load() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        return _default()
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for key, value in _default().items():
        data.setdefault(key, value)
    return data


def save(data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def new_id(data: dict) -> int:
    i = data["next_id"]
    data["next_id"] += 1
    return i


def today() -> str:
    return date.today().isoformat()
