"""
Celery application factory and beat schedule.
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
    task_time_limit=10 * 60,        # 10 min hard limit
    task_soft_time_limit=8 * 60,    # 8 min soft limit → SoftTimeLimitExceeded
    worker_prefetch_multiplier=1,   # fair dispatch for long tasks
    task_acks_late=True,            # only ack after task completes
    beat_schedule={
        # Live ticks — every 60 seconds during market hours
        "fetch-all-ticks": {
            "task": "app.tasks.fetch_all_ticks",
            "schedule": celery_timedelta(seconds=60),
            "options": {"expires": 55},
        },
        # 1h candles — every 5 minutes (pick up the latest completed candle)
        "refresh-ohlcv-1h": {
            "task": "app.tasks.refresh_ohlcv",
            "args": ["1h", 10],
            "schedule": celery_timedelta(minutes=5),
            "options": {"expires": 270},
        },
        # 4h candles — every 30 minutes
        "refresh-ohlcv-4h": {
            "task": "app.tasks.refresh_ohlcv",
            "args": ["4h", 5],
            "schedule": celery_timedelta(minutes=30),
            "options": {"expires": 1700},
        },
        # Daily candles — every hour
        "refresh-ohlcv-1d": {
            "task": "app.tasks.refresh_ohlcv",
            "args": ["1d", 2],
            "schedule": celery_timedelta(hours=1),
            "options": {"expires": 3500},
        },
    },
)
