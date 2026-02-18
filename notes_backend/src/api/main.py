from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .core.config import get_settings
from .db.session import engine
from .routers import auth, notes, tags

openapi_tags = [
    {"name": "auth", "description": "Authentication (register/login/me)."},
    {"name": "tags", "description": "Tag CRUD."},
    {"name": "notes", "description": "Notes CRUD + search + pin/favorite."},
]


# PUBLIC_INTERFACE
def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: app instance exposing REST endpoints for authentication, notes, and tags.
    """
    settings = get_settings()

    app = FastAPI(
        title="NoteMaster API",
        description="Minimal notes backend with authentication, tags, search, and pin/favorite.",
        version="0.1.0",
        openapi_tags=openapi_tags,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["auth"], summary="Health check", operation_id="health_check")
    async def health_check():
        """Health check endpoint."""
        return {"message": "Healthy"}

    @app.on_event("startup")
    async def _startup_db_check():
        # Ensure DB connection works; helps surface config problems early.
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    app.include_router(auth.router)
    app.include_router(tags.router)
    app.include_router(notes.router)
    return app


app = create_app()
