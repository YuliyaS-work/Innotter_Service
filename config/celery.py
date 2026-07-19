import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'innotter_service.settings')

app = Celery('innotter_service')
app.config_from_object('django.conf:settings', namespace="CELERY")
app.conf.update(CELERY_IMPORTS=('innotter.tasks',),)

app.autodiscover_tasks(['innotter'])