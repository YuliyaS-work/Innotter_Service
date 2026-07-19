from celery import shared_task
from .models import Page

import config

@shared_task
def unblock_page(page_id):
    page = Page.objects.get(pk=page_id)

    if page.is_blocked:
        page.is_blocked = False
        page.save(update_fields=["is_blocked"])