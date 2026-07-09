from __future__ import annotations

import re
from pathlib import Path

_SAFE_STORAGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def sanitize_storage_id(value: object, *, field_name: str) -> str:
    """Return a filesystem-safe workflow/run id or raise ValueError."""
    text = str(value or "").strip()
    if not _SAFE_STORAGE_ID_RE.fullmatch(text):
        raise ValueError(
            f"{field_name} must be 1-128 chars and contain only letters, "
            "numbers, '_' or '-'"
        )
    return text


def safe_child_dir(root: Path, child_id: object, *, field_name: str) -> Path:
    safe_id = sanitize_storage_id(child_id, field_name=field_name)
    resolved_root = root.resolve()
    resolved_child = (resolved_root / safe_id).resolve()
    if resolved_child != resolved_root and resolved_root not in resolved_child.parents:
        raise ValueError(f"{field_name} resolves outside storage root")
    return resolved_child
