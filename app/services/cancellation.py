"""In-memory cancellation registry for in-flight workflow runs.

Lightweight by design: a thread-safe set of workflow_ids that have been
marked for cancellation. The workflow runner polls is_cancelled() at
step boundaries and raises WorkflowCancelledError when the flag is set.

Single-process FastAPI deployment is assumed. Switch to Redis / DB if
multi-worker deployment is ever introduced.
"""

from __future__ import annotations

import threading
from typing import Set


_lock = threading.Lock()
_cancelled: Set[str] = set()


def request_cancel(workflow_id: str) -> None:
    """Mark a workflow as cancel-requested. Idempotent."""
    if not workflow_id:
        return
    with _lock:
        _cancelled.add(str(workflow_id))


def is_cancelled(workflow_id: str) -> bool:
    """Return True if the workflow has been marked for cancellation."""
    if not workflow_id:
        return False
    with _lock:
        return str(workflow_id) in _cancelled


def clear(workflow_id: str) -> None:
    """Remove the workflow from the registry (on terminal state)."""
    if not workflow_id:
        return
    with _lock:
        _cancelled.discard(str(workflow_id))
