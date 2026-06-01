"""
API Schemas for Market Data
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SymbolBase(BaseModel):
    symbol: str
    name: str
    type: str
    description: Optional[str] = None


class SymbolResponse(SymbolBase):
    id: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OHLCVData(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataResponse(BaseModel):
    symbol: str
    timeframe: str
    data: list[OHLCVData]
    count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
