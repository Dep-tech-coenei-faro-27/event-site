import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.media import MediaFiles
from app.core.middleware import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    UnhandledExceptionMiddleware,
)
from app.domains.auth.router import router as auth_router
from app.domains.health.router import router as health_router


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    docs = settings.ENVIRONMENT != "prod"
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )

    settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    app.mount("/media", MediaFiles(directory=settings.MEDIA_DIR), name="media")

    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

    register_exception_handlers(app)

    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
