from pathlib import PurePosixPath

from fastapi import HTTPException, status
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

ALLOWED_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


class MediaFiles(StaticFiles):
    """Serve only image files, and never as something a browser can run.

    Other extensions (html, svg, js) and hidden files answer 404, so an
    upload cannot become a page on the API origin.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        file_path = PurePosixPath(path)
        hidden = any(part.startswith(".") for part in file_path.parts)
        if hidden or file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        response = await super().get_response(path, scope)
        response.headers["Content-Security-Policy"] = "sandbox"
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response
