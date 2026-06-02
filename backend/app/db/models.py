"""
SQLAlchemy ORM Models
"""

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.base import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False)  # forex, commodity, index, bond
    description = Column(Text)
    decimals = Column(Integer, default=5)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_symbol_active", "symbol", "active"),
        Index("idx_symbol_type", "asset_type"),
    )


class MarketDataOHLCV(Base):
    """OHLCV candlestick data — primary time series table."""

    __tablename__ = "market_data_ohlcv"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)   # 1m, 5m, 15m, 1h, 4h, 1d
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    data_source = Column(String(50), nullable=False, default="unknown")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Prevents duplicate candles for same symbol+timeframe+timestamp
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_ohlcv_symbol_tf_ts"),
        Index("idx_ohlcv_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
        Index("idx_ohlcv_timestamp", "timestamp"),
    )


class TickDataRecord(Base):
    """Real-time tick data (bid/ask)."""

    __tablename__ = "tick_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    spread = Column(Float, nullable=False, default=0.0)
    volume = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    data_source = Column(String(50), nullable=False, default="unknown")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_tick_symbol_ts", "symbol", "timestamp"),
    )
