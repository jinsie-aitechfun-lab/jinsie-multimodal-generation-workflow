from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, TypeVar


T = TypeVar("T")
_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


def path_lock(path: Path) -> threading.RLock:
    """Return the process-wide re-entrant lock for a normalized JSON path."""
    key = str(path.expanduser().resolve())
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


def read_json(path: Path, default: T | None = None) -> Any | T | None:
    lock = path_lock(path)
    with lock:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def _write_unlocked(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def write_json_atomic(path: Path, payload: Any) -> None:
    with path_lock(path):
        _write_unlocked(path, payload)


def update_json_atomic(
    path: Path,
    updater: Callable[[Any], Any],
    *,
    default: Any = None,
) -> Any:
    """Read, update and atomically replace JSON while holding one path lock."""
    with path_lock(path):
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                current = json.load(handle)
        else:
            current = default
        updated = updater(current)
        _write_unlocked(path, updated)
        return updated
