"""Short-lived conversational context for stateless OpenAI-compatible providers.

Claude sessions already provide server-side conversation state.  OpenAI-style
gateways do not, so keep a small text-only transcript locally and send it with
the next request.  Images are deliberately not persisted here; the Telegram
bot keeps only the latest image in memory for follow-up questions.
"""

from __future__ import annotations

import json
from pathlib import Path

from .paths import OG_HOME

STORE_FILE = OG_HOME / "provider_context.json"
MAX_MESSAGES = 12  # six user/assistant turns
MAX_MESSAGE_CHARS = 8000


def _load() -> dict[str, list[dict[str, str]]]:
    if not STORE_FILE.is_file():
        return {}
    try:
        data = json.loads(STORE_FILE.read_text())
    except (OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, list[dict[str, str]]]) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(STORE_FILE) + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.chmod(0o600)
    tmp.replace(STORE_FILE)


def get(chat_id: int) -> list[dict[str, str]]:
    """Return the bounded text transcript for ``chat_id``."""
    rows = _load().get(str(chat_id), [])
    if not isinstance(rows, list):
        return []
    return [
        {"role": row["role"], "content": row["content"][:MAX_MESSAGE_CHARS]}
        for row in rows
        if isinstance(row, dict)
        and row.get("role") in {"user", "assistant"}
        and isinstance(row.get("content"), str)
    ][-MAX_MESSAGES:]


def append(chat_id: int, user_text: str, assistant_text: str) -> None:
    """Append one completed turn, retaining only recent text."""
    data = _load()
    rows = data.setdefault(str(chat_id), [])
    if not isinstance(rows, list):
        rows = []
        data[str(chat_id)] = rows
    rows.extend(
        [
            {"role": "user", "content": user_text[:MAX_MESSAGE_CHARS]},
            {"role": "assistant", "content": assistant_text[:MAX_MESSAGE_CHARS]},
        ]
    )
    data[str(chat_id)] = rows[-MAX_MESSAGES:]
    _save(data)


def reset(chat_id: int) -> None:
    """Forget provider context for one chat."""
    data = _load()
    if data.pop(str(chat_id), None) is not None:
        _save(data)
