from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import graph as graph_api
from app.api import meta, study, words
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trellis API",
        version="0.1.0",
        description="Vocabulary knowledge graph, dictionary management and spaced repetition.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    app.include_router(words.router)
    app.include_router(graph_api.router)
    app.include_router(study.router)
    app.include_router(meta.router)

    dist = settings.legacy_root / "frontend" / "dist"
    if dist.exists():
        static_dir = dist.resolve()

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            candidate = (static_dir / full_path).resolve()
            if candidate.is_file() and str(candidate).startswith(str(static_dir)):
                return FileResponse(candidate)
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()
