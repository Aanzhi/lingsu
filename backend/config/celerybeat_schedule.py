"""Periodic task schedule for Celery beat.

The schedule is intentionally short and run inside the worker's transaction so a
stuck beat tick does not skip the next run.
"""

from celery.schedules import crontab


CELERY_BEAT_SCHEDULE = {
    "purge-trashed-projects-daily": {
        "task": "apps.core.tasks.purge_trashed_projects",
        # Run at 03:00 server time every day; 30-day retention is hard-coded in the task.
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"retention_days": 30},
    },
}
