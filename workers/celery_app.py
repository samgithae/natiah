from celery import Celery

from app.core.config import settings


celery_app = Celery("natiah_workers", broker=settings.redis_url, backend=settings.redis_url)
celery_app.autodiscover_tasks(["workers"])
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "scheduled-tick": {
        "task": "workers.tasks.scheduled_tick",
        "schedule": 60.0,
    }
}
