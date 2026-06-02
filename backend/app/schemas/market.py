"""
API Schemas for Market Data
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SymbolBase(BaseModel):
    symbol: str
    name: str
    asset_type: str
    decimals: int = 2


class SymbolCreate(SymbolBase):
    pass


class SymbolResponse(SymbolBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active: bool
    created_at: datetime


class OHLCVData(BaseModel):
    """OHLCV candlestick data"""

    symbol: str
    timeframe: str
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trading volume")
    timestamp: datetime = Field(..., description="Candle timestamp")
    data_source: str = Field(..., description="Data provider")


class OHLCVResponse(BaseModel):
    """Response for OHLCV data"""

    symbol: str
    timeframe: str
    count: int
    data: List[OHLCVData]


class TickData(BaseModel):
    """Real-time tick data with bid/ask"""

    symbol: str
    bid: float = Field(..., gt=0, description="Bid price")
    ask: float = Field(..., gt=0, description="Ask price")
    price: float = Field(..., gt=0, description="Mid price")
    volume: float = Field(..., ge=0, description="Tick volume")
    timestamp: datetime = Field(..., description="Tick timestamp")
    data_source: str = Field(..., description="Data provider")


class LatestTickResponse(BaseModel):
    """Latest tick data for a symbol"""

    symbol: str
    bid: float
    ask: float
    price: float
    spread: float
    volume: float
    timestamp: datetime
    change_pct: Optional[float] = None


class MarketDataResponse(BaseModel):
    """Generic market data response"""

    symbol: str
    timeframe: str
    data: List[OHLCVData]
    count: int


class HealthResponse(BaseModel):
    """API health status"""

    status: str
    version: str
    environment: str
    timestamp: datetime
