"""
Volatility Engine — orchestrates calculations over live OHLCV data.
"""

from datetime import UTC, datetime
from typing import List

from app.core.logger import get_logger
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.volatility import calculator as calc
from app.services.volatility.schemas import VolatilityReading, VolatilitySummary

logger = get_logger(__name__)

_LOOKBACK  = 60   # candles to fetch per symbol
_TIMEFRAME = "1h"


class VolatilityEngine:
    def __init__(self, provider: BaseMarketDataProvider) -> None:
        self.provider = provider

    # ── Single symbol ─────────────────────────────────────────────

    async def analyze(
        self,
        symbol:    str = "XAUUSD",
        timeframe: str = _TIMEFRAME,
        limit:     int = _LOOKBACK,
    ) -> VolatilityReading:
        candles = await self.provider.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

        if len(candles) < 15:
            return self._empty(symbol, timeframe)

        last = candles[-1]
        price = last.close or 1.0

        # ATR series (14-period)
        atr_series = calc.compute_atr(candles, period=14)
        atr14 = atr_series[-1] if atr_series else 0.0
        atr_pct = atr14 / price * 100

        # ATR z-score vs 50-period history
        atr_history = atr_series[-50:] if len(atr_series) >= 50 else atr_series
        atr_z = calc._zscore(atr14, atr_history)

        # Realized volatility
        rv10 = calc.realized_vol(candles, 10)
        rv20 = calc.realized_vol(candles, 20)
        rv50 = calc.realized_vol(candles, 50)

        # Range analysis
        cr_pct   = calc.candle_range_pct(last)
        avg_r    = calc.avg_range_pct(candles, 20)
        r_compression = cr_pct / avg_r if avg_r > 0 else 1.0
        body_r   = calc.body_ratio(last)

        # Regime
        regime, vol_score, comp_score, exp_score = calc.classify_vol_regime(
            atr_pct, atr_z, rv20, r_compression
        )

        # Signals
        signals = calc.generate_vol_signals(
            regime, atr_pct, atr_z, r_compression, rv20, body_r
        )

        return VolatilityReading(
            symbol=symbol, timeframe=timeframe, timestamp=datetime.now(UTC),
            atr=round(atr14, 5),
            atr_pct=round(atr_pct, 4),
            atr_14=round(atr14, 5),
            atr_zscore=round(atr_z, 3),
            realized_vol_10=round(rv10, 2),
            realized_vol_20=round(rv20, 2),
            realized_vol_50=round(rv50, 2),
            candle_range_pct=round(cr_pct, 4),
            avg_range_20=round(avg_r, 4),
            range_compression=round(r_compression, 3),
            body_to_range_ratio=round(body_r, 3),
            regime=regime,
            regime_score=vol_score,
            compression_score=comp_score,
            expansion_score=exp_score,
            signals=signals,
            candles_analyzed=len(candles),
        )

    # ── Multi-symbol summary ──────────────────────────────────────

    async def analyze_all(self) -> VolatilitySummary:
        symbols = ["XAUUSD", "DXY", "SPX", "VIX"]
        readings = {}

        for sym in symbols:
            try:
                r = await self.analyze(sym)
                readings[sym] = r.model_dump()
            except Exception as e:
                logger.warning(f"Volatility analysis failed for {sym}: {e}")

        gold = readings.get("XAUUSD", {})
        vix_tick = await self.provider.fetch_latest_tick("VIX")
        vix_price = vix_tick.price

        return VolatilitySummary(
            timestamp=datetime.now(UTC),
            readings=readings,
            gold_regime=gold.get("regime", "unknown"),
            gold_vol_score=gold.get("regime_score", 0.0),
            market_vol_regime=calc.classify_market_vol_regime(
                vix_price, gold.get("atr_pct", 0.5)
            ),
            vix_level=round(vix_price, 2),
            vix_regime=calc.classify_vix_regime(vix_price),
        )

    def _empty(self, symbol: str, timeframe: str) -> VolatilityReading:
        return VolatilityReading(
            symbol=symbol, timeframe=timeframe, timestamp=datetime.now(UTC),
            atr=0, atr_pct=0, atr_14=0, atr_zscore=0,
            realized_vol_10=0, realized_vol_20=0, realized_vol_50=0,
            candle_range_pct=0, avg_range_20=0, range_compression=1,
            body_to_range_ratio=0,
            regime="unknown", regime_score=0, compression_score=0, expansion_score=0,
        )
