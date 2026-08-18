"""Celery application shared by document, AI and notification tasks."""

import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("kechuang_ai_workbench")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule_filename = "/tmp/celerybeat-schedule"

# Pull periodic tasks from a dedicated module so settings.py stays focused on
# transport / security knobs. Beat will fail to start if this file is missing.
from config.celerybeat_schedule import CELERY_BEAT_SCHEDULE  # noqa: E402

app.conf.beat_schedule = CELERY_BEAT_SCHEDULE

