from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pricing_intel.api.routers import catalog, collection
from pricing_intel.db.pool import close_pool, get_pool
from pricing_intel.jobs.app import app as procrastinate_app
from pricing_intel.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await get_pool().open()
    await procrastinate_app.open_async()
    try:
        yield
    finally:
        await procrastinate_app.close_async()
        await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pricing Intelligence API",
        description=(
            "Discovers offers across sources, matches them to canonical "
            "variants, and reports an explainable price comparison."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(collection.router)
    app.include_router(catalog.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        async with get_pool().connection() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ok"}

    return app


app = create_app()
