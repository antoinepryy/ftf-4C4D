from celery import Celery
from app.config import get_settings

_settings = get_settings()
celery = Celery("ftf", broker=_settings.broker_url, backend=_settings.broker_url,
                include=["app.tasks"])
celery.conf.task_track_started = True
