from __future__ import annotations

from starlette.responses import Response
from starlette.staticfiles import StaticFiles


class RevalidatingStaticFiles(StaticFiles):
    """Keep generated, overwrite-in-place assets cacheable but revalidated."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code in {200, 304}:
            response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
        return response
