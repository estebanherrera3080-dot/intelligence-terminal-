"""
API v1 — REST + WebSocket routes
"""

from fastapi import APIRouter

from app.api.v1.routes.correlation import router as corr_router
from app.api.v1.routes.intelligence import router as intel_router
from app.api.v1.routes.macro import router as macro_router
from app.api.v1.routes.market import router as market_router
from app.api.v1.routes.news import router as news_router
from app.api.v1.routes.smc import router as smc_router
from app.api.v1.routes.volatility import router as vol_router
from app.api.v1.routes.ws import router as ws_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(market_router)
api_router.include_router(macro_router)
api_router.include_router(smc_router)
api_router.include_router(vol_router)
api_router.include_router(corr_router)
api_router.include_router(intel_router)
api_router.include_router(news_router)
api_router.include_router(ws_router)

__all__ = ["api_router"]
