"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events
    """
    # Startup
    logger.info(f"Starting Jardin Secreto v{app.version}")
    logger.info(f"Environment: {settings.environment}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Jardin Secreto")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(
        title="Jardin Secreto Terminal API",
        description="Institutional Gold Trading Terminal",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": app.version,
            "environment": settings.environment,
        }

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Welcome to Jardin Secreto Terminal API",
            "documentation": "/docs",
            "version": app.version,
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
