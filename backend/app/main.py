from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.core.config import PROJECT_ROOT, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.database.session import init_database

logger = logging.getLogger("workspace.main")


def _resolve_frontend_dist_dir() -> Path | None:
    """Locate compiled React frontend assets in either dev or PyInstaller bundle mode."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "frontend_dist")  # type: ignore[attr-defined]
    candidates.append(PROJECT_ROOT / "frontend" / "dist")
    for path in candidates:
        if path.exists() and (path / "index.html").is_file():
            return path
    return None


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting %s v%s (%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    init_database()
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Local-first, multi-provider Personal AI Workspace API.",
        docs_url=f"{settings.api_v1_prefix}/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)
    application.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # In production / packaged desktop mode, serve compiled React frontend from FastAPI
    dist_dir = _resolve_frontend_dist_dir()
    if dist_dir is not None:
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            application.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="frontend_assets",
            )

        index_html = dist_dir / "index.html"

        @application.get("/", include_in_schema=False)
        def serve_spa_root() -> FileResponse:
            return FileResponse(str(index_html))

    return application


app = create_app()
