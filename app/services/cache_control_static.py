from __future__ import annotations

from urllib.parse import parse_qs

from starlette.responses import Response
from starlette.staticfiles import StaticFiles


class RevalidatingStaticFiles(StaticFiles):
    """Keep generated, overwrite-in-place assets cacheable but revalidated."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code in {200, 304}:
            query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
            is_versioned_generated_image = (
                path.startswith("mock/image/")
                and path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                and bool(query.get("v", [""])[0])
            )
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable"
                if is_versioned_generated_image
                else "public, max-age=0, must-revalidate"
            )
        return response
