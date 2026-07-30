"""
This module contains Celery tasks for managing user pages and related data.

The `unblock_page` task removes the block status from a page if it is blocked.
The `delete_user_data` task deletes all data that belongs to a user. It removes
the user's pages and also deletes likes and followers connected to these pages.
If a database error happens, the task will try again later using a waiting queue.
"""
import logging

from celery import shared_task
from django.db.models import F
from django.utils import timezone

from .models import Page, Likes, Followers, Post

logger = logging.getLogger(__name__)

@shared_task
def unblock_pages() -> None:
    """Unblocks the pages if they are currently blocked."""
    expired_pages = Page.objects.filter(
        is_blocked=True,
        unblock_date__lte=timezone.now()
    )

    for page in expired_pages:
        try:
            page.is_blocked = False
            page.unblock_date = None
            page.save(update_fields=["is_blocked", "unblock_date"])
            logger.info(f"Automatically unblocked page ID={page.id}")

        except Exception as e:
            logger.error(f"[TASK] Failed to unblock page ID={page.id}: {e}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def delete_user_data(self, user_id: str) -> None:
    """Deletes all data related to the user, including pages, posts, likes, and followers."""

    # delete pages and their associated posts, followers and likes
    for page in Page.objects.filter(user_id=user_id).iterator():
        page.delete()

    # delete like records of a user and update a number of likes for each post
    for like in Likes.objects.filter(user_id=user_id).iterator():
        (Post.objects.filter(pk=like.post_id, likes_count__gt=0)
         .update(likes_count=F("likes_count") - 1))
        like.delete()

    # delete follower records of a user and update a number of followers for each page
    for follower in Followers.objects.filter(user_id=user_id).iterator():
        (Page.objects.filter(pk=follower.page_id, followers_count__gt=0)
         .update(followers_count=F("followers_count") - 1))
        follower.delete()

    logger.info(f"User data were deleted successfully. user ID={user_id}")