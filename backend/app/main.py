import os

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from app.core.config import settings
from app.domains.health.router import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

    os.makedirs("media", exist_ok=True)

    app.mount("/media", StaticFiles(directory="media"), name="media")

    app.include_router(health_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
