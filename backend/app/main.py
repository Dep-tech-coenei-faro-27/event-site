from fastapi import FastAPI

from app.core.config import settings
from app.domains.health.router import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"status": "API is running"}

    app.include_router(health_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
