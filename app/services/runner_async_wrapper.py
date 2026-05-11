from __future__ import annotations

import threading
import traceback
from queue import Queue
from typing import Any, Callable, Dict

from app.schemas.workflow import WorkflowRunRequest


ASYNC_QUEUE: "Queue[Dict[str, Any]]" = Queue()


def enqueue_run_task(
    task_data: Dict[str, Any],
    callback: Callable[[Dict[str, Any]], None],
) -> None:
    ASYNC_QUEUE.put({"task_data": task_data, "callback": callback})


def worker_loop() -> None:
    from app.services.runner import WorkflowRunner

    while True:
        item = ASYNC_QUEUE.get()
        try:
            task_data = item["task_data"]
            callback = item["callback"]

            runner = WorkflowRunner()
            request = WorkflowRunRequest(**task_data)
            result = runner.run(request)

            if hasattr(result, "model_dump"):
                payload = result.model_dump()
            elif isinstance(result, dict):
                payload = result
            else:
                payload = dict(result)

            callback(payload)
        except Exception as error:
            print("[AsyncRunner] task failed:", error)
            traceback.print_exc()
        finally:
            ASYNC_QUEUE.task_done()


threading.Thread(
    target=worker_loop,
    daemon=True,
    name="RunnerAsyncWorker",
).start()
