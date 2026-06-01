"""
Celery Configuration
Used for async tasks and scheduled jobs
"""

from celery import Celery
from app.core.config import settings

app = Celery(
    'jardin-secreto',
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Load config
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
)
