"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from datetime import datetime, UTC

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logger import get_logger
from app.api.v1 import api_router

logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{app.version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    yield

    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(
        title=f"{settings.app_name} API",
        description="Institutional Gold Trading Terminal",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )

    # Security: Trusted Host Middleware
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts,
        )

    # Security: CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        max_age=3600,
    )

    # Rate limiting exception handler
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": exc.detail,
            },
        )

    # Include API routes
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health")
    @limiter.limit("60/minute")
    async def health_check(request: Request):
        """
        Health check endpoint
        Returns service status and version information
        """
        return {
            "status": "healthy",
            "version": app.version,
            "environment": settings.environment,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Root endpoint
    @app.get("/")
    async def root():
        """
        Welcome endpoint
        Provides API documentation links
        """
        return {
            "message": "Welcome to Intelligence Terminal API",
            "documentation": "/docs" if settings.debug else "/redoc",
            "version": app.version,
            "status": "running",
        }

    # App state for rate limiter
    app.state.limiter = limiter
    app.state.limiter_exception_handler = rate_limit_handler

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
