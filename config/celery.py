"""
Celery application configuration for the Innotter Service.

This module initializes the Celery app, loads Django settings, applies
Celery specific configuration and enables automatic discovery of task
modules inside the `innotter` application.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'config.settings')

app = Celery('innotter_service')
app.config_from_object('django.conf:settings', namespace="CELERY")
app.conf.update(CELERY_IMPORTS=('innotter.tasks',),)

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'unblock-pages-every-minute': {
        'task': 'innotter.tasks.unblock_pages',
        'schedule': crontab(minute='*'),
    },
}