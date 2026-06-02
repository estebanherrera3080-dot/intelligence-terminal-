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
    Handle startup and shutdown events.
    """
    logger.info(f"Starting {settings.app_name} v{app.version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Attempt Redis connection — TickStore falls back to memory if unavailable
    from app.core.redis_client import get_redis
    r = await get_redis()
    if r:
        logger.info("Redis ready — TickStore using Redis backend")
    else:
        logger.warning("Redis not available — TickStore using in-memory fallback")

    # Warm the tick cache on startup so the dashboard is live immediately.
    # Uses 7 API credits (one per symbol); skipped if cache already has data.
    await _warm_tick_cache()

    yield

    # Shutdown
    from app.core.redis_client import close_redis
    await close_redis()
    logger.info(f"Shutting down {settings.app_name}")


async def _warm_tick_cache() -> None:
    """
    Pre-populate the tick cache at startup when it is cold.
    Runs a single provider fetch so the dashboard has data immediately,
    without waiting up to 5 minutes for the first Celery tier1 run.
    """
    from app.services.cache.tick_store import tick_store
    from app.services.market_data.providers import get_active_provider
    from app.services.market_data.service import TRACKED_SYMBOLS

    existing = await tick_store.get_snapshot()
    if existing:
        logger.info(f"Tick cache already warm ({len(existing)} symbols) — skipping startup fetch")
        return

    logger.info("Tick cache cold — warming on startup...")
    provider = get_active_provider()
    snapshot: dict = {}

    for symbol in TRACKED_SYMBOLS:
        try:
            tick = await provider.fetch_latest_tick(symbol)
            payload = {
                "price":     tick.price,
                "bid":       tick.bid,
                "ask":       tick.ask,
                "spread":    round(tick.ask - tick.bid, 8),
                "volume":    tick.volume,
                "timestamp": tick.timestamp.isoformat(),
                "source":    tick.data_source,
            }
            await tick_store.set_tick(symbol, payload)
            snapshot[symbol] = payload
        except Exception as exc:
            logger.warning(f"Startup fetch failed for {symbol}: {exc}")

    if snapshot:
        await tick_store.set_snapshot(snapshot)
        logger.info(f"Tick cache warmed — {len(snapshot)}/{len(TRACKED_SYMBOLS)} symbols ready")


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
