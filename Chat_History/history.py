"""JSON-file chat history in the project folder.
Stores only user query + bot response per turn.
"""

import json
import os
import threading

import config

_LOCK = threading.Lock()


def _ensure_history_file():
    """Create chat_history.json if it does not already exist."""
    if not os.path.exists(config.HISTORY_FILE):
        with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)


def _read_all() -> dict:
    _ensure_history_file()

    try:
        with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_all(data: dict):
    tmp = config.HISTORY_FILE + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    os.replace(tmp, config.HISTORY_FILE)


def load_history(
    session_id: str,
    last_n: int = config.HISTORY_TURNS_USED
) -> list[dict]:

    with _LOCK:
        return _read_all().get(session_id, [])[-last_n:]


def get_full_history(session_id: str) -> list[dict]:

    with _LOCK:
        return _read_all().get(session_id, [])


def save_turn(session_id: str, user: str, assistant: str, company: str | None, question_type: str):
    with _LOCK:
        data = _read_all()
        turns = data.setdefault(session_id, [])
        turns.append({
            "user": user,
            "assistant": assistant,
            "company": company,              # "InsuranceDekho" | "Yubi" | None
            "question_type": question_type,  # company_query | unclassified | general | irrelevant
        })
        data[session_id] = turns[-config.HISTORY_MAX_STORED:]
        _write_all(data)


def clear_history(session_id: str) -> bool:

    with _LOCK:
        data = _read_all()

        existed = data.pop(session_id, None) is not None

        _write_all(data)

        return existed


def history_as_text(history: list[dict]) -> str:

    if not history:
        return "(no previous conversation)"

    return "\n\n".join(
        f"User: {t['user']}\nAssistant: {t['assistant']}"
        for t in history
    )