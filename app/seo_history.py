import json
import os
from pathlib import Path

_HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "keyphrase_history.json"


def _load() -> list[str]:
    if not _HISTORY_PATH.exists():
        return []
    try:
        with open(_HISTORY_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def was_keyphrase_used(keyphrase: str) -> bool:
    normalized = keyphrase.strip().lower()
    return normalized in {k.lower() for k in _load()}


def record_keyphrase(keyphrase: str) -> None:
    normalized = keyphrase.strip()
    if not normalized:
        return
    history = _load()
    if normalized.lower() not in {k.lower() for k in history}:
        history.append(normalized)
        os.makedirs(_HISTORY_PATH.parent, exist_ok=True)
        with open(_HISTORY_PATH, "w") as f:
            json.dump(history, f, indent=2)
