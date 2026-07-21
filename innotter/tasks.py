"""
This module contains Celery tasks for managing user pages and related data.

The `unblock_page` task removes the block status from a page if it is blocked.
The `delete_user_data` task deletes all data that belongs to a user. It removes
the user's pages and also deletes likes and followers connected to these pages.
If a database error happens, the task will try again later using a waiting queue.
"""
from typing import Any

from celery import shared_task
from django.core.exceptions import ValidationError
from pymysql import DatabaseError

from .models import Page, Likes, Followers, Post

from django.db.models import F

@shared_task
def unblock_page(page_id: int) -> None:
    """Unblocks the page if it is currently blocked."""
    page = Page.objects.get(pk=page_id)

    if page.is_blocked:
        page.is_blocked = False
        page.save(update_fields=["is_blocked"])


@shared_task(bind=True)
def delete_user_data(self, **kwargs: dict[str, Any]) -> None:
    """Deletes all data related to the user, including pages, posts, likes, and followers."""
    user_id = kwargs.get("user_id")
    if not user_id:
        raise ValidationError("Invalid message, user_id is required")

    try:
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

    except (DatabaseError, TimeoutError) as exc:
        raise self.retry(
            exc=exc,
            countdown=30,
            queue='waiting-queue'
        )