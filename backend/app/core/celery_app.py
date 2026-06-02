"""
Celery application factory and beat schedule.

Credit budget (Twelve Data Basic — 800 credits/day, 8 h active):
  Tier 1 ticks  (XAUUSD, DXY, VIX)         3 × 12/h × 8 h = 288 credits
  Tier 2 ticks  (US10Y, US02Y, SPX, NDX)   4 ×  4/h × 8 h = 128 credits
  OHLCV 1h      (7 symbols, every 65 min)   7 ×  7 cycles  =  49 credits
  OHLCV 4h      (7 symbols, every 4 h)      7 ×  2 cycles  =  14 credits
  OHLCV 1d      (7 symbols, once/day)       7 ×  1 cycle   =   7 credits
  ─────────────────────────────────────────────────────────────────────
  TOTAL                                                       486 credits
  BUFFER                                                      314 credits
"""

from celery import Celery
from celery.schedules import timedelta as celery_timedelta

from app.core.config import settings

celery_app = Celery(
    "intelligence_terminal",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=10 * 60,
    task_soft_time_limit=8 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={

        # ── Tier 1: XAUUSD · DXY · VIX ──────────────────────────── #
        # Primary gold drivers — need freshest price data.
        # 3 API credits per run × every 5 min.
        "fetch-ticks-tier1": {
            "task": "app.tasks.fetch_ticks_tier1",
            "schedule": celery_timedelta(minutes=5),
            "options": {"expires": 290},
        },

        # ── Tier 2: US10Y · US02Y · SPX · NDX ───────────────────── #
        # Macro context instruments — slower-moving, 15 min is enough.
        # 4 API credits per run × every 15 min.
        "fetch-ticks-tier2": {
            "task": "app.tasks.fetch_ticks_tier2",
            "schedule": celery_timedelta(minutes=15),
            "options": {"expires": 890},
        },

        # ── OHLCV 1h ─────────────────────────────────────────────── #
        # 65 min interval ensures we always capture the latest closed
        # 1h candle without hammering the API every 5 min.
        # 7 API credits per run.
        "refresh-ohlcv-1h": {
            "task": "app.tasks.refresh_ohlcv",
            "args": ["1h", 3],
            "schedule": celery_timedelta(minutes=65),
            "options": {"expires": 3800},
        },

        # ── OHLCV 4h ─────────────────────────────────────────────── #
        # 7 API credits per run × 2 runs/day.
        "refresh-ohlcv-4h": {
            "task": "app.tasks.refresh_ohlcv",
            "args": ["4h", 2],
            "schedule": celery_timedelta(hours=4),
            "options": {"expires": 14000},
        },

        # ── OHLCV 1d ─────────────────────────────────────────────── #
        # 7 API credits per run × 1 run/day.
        "refresh-ohlcv-1d": {
            "task": "app.tasks.refresh_ohlcv",
            "args": ["1d", 2],
            "schedule": celery_timedelta(hours=24),
            "options": {"expires": 86000},
        },

    },
)
