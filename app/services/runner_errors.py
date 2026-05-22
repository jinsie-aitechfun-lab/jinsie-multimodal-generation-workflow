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
