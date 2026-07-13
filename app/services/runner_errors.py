"""Custom exception types raised by the workflow runner and its support
modules.

Lifted out of runner.py so that extracted support modules
(runner_render_plan.py, runner_image_review.py, runner_session.py, ...)
can raise these without creating an import cycle back into runner.py.
"""

from __future__ import annotations


class UnknownStepError(Exception):
    """Raised by WorkflowRunner.run when an unknown step name appears in
    the request."""


class UnknownVideoProviderError(Exception):
    """Raised when a request asks for a video_provider that the runner
    does not know how to dispatch (e.g. neither mock / kling / jimeng)."""


class WorkflowCancelledError(Exception):
    """Raised by the workflow runner when a cancel request is observed at
    a step boundary. Carries the workflow_id and any partial outputs that
    were aggregated before cancellation so the caller can persist them."""

    def __init__(self, workflow_id, partial_outputs=None):
        super().__init__(f"workflow {workflow_id} cancelled")
        self.workflow_id = workflow_id
        self.partial_outputs = partial_outputs or {}
