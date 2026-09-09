"""FastAPI application factory and route mounting."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, insights, narratives, races
from app.api.schemas import HealthResponse


def create_app(cors_origins: Optional[list[str]] = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="F1 Race Intelligence API",
        description="Deterministic analytics, statistical evidence, rule-based insights, and grounded AI narratives for Formula 1.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    if cors_origins is None:
        raw_origins = os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        )
        cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok", version="0.1.0")

    # Mount API routers
    app.include_router(races.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(insights.router, prefix="/api")
    app.include_router(narratives.router, prefix="/api")

    return app


app = create_app()
