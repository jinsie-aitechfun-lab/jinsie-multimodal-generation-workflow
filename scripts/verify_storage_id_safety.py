from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import get_workflow_status
from app.services.storage_ids import safe_child_dir, sanitize_storage_id


def _assert_raises(error_type, fn, *args, **kwargs) -> Exception:
    try:
        fn(*args, **kwargs)
    except error_type as error:
        return error
    raise AssertionError(f"expected {error_type.__name__}")


def main() -> None:
    assert sanitize_storage_id("wf_123-ok", field_name="workflow_id") == "wf_123-ok"
    assert sanitize_storage_id(" run_verify ", field_name="run_id") == "run_verify"

    for value in ["", "../escape", "a/b", "bad id", ".hidden"]:
        _assert_raises(ValueError, sanitize_storage_id, value, field_name="workflow_id")

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        child = safe_child_dir(root, "wf_safe-1", field_name="workflow_id")
        assert child == (root / "wf_safe-1").resolve()
        _assert_raises(ValueError, safe_child_dir, root, "../escape", field_name="workflow_id")

    error = _assert_raises(HTTPException, get_workflow_status, "../escape")
    assert error.status_code == 400

    print("verify_storage_id_safety: ok")


if __name__ == "__main__":
    main()
