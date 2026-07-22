"""
This file contains Django models for pages, posts, tags, likes and followers.
It shows tha data structure and how models are connected.
Pages connect to Posts through a one‑to‑many relation.
Posts connect to Likes through a one‑to‑many relation.
Pages connect to Followers through one‑to‑many relation.
"""

from django.db import models


class Page(models.Model):
    """ Django model for a page that stores its info and follower count."""
    name = models.CharField(max_length=50, unique=True, verbose_name="Page name")
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="Page description")
    user_id = models.CharField(max_length=36, verbose_name="User ID")
    group_id = models.PositiveSmallIntegerField(null=True, verbose_name="Group ID of a user")
    image_url = models.CharField(max_length=255, null=True, blank=True, verbose_name="Image URL")
    is_blocked = models.BooleanField(default=False, verbose_name="Page status")
    unblock_date = models.DateTimeField(null=True, blank=True, verbose_name="Unblocked time")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created time")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated time")
    tags = models.ManyToManyField("Tag", blank=True, verbose_name="Tags")
    followers_count = models.PositiveSmallIntegerField(default=0, verbose_name="Number of followers")
    task_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Pages"
        verbose_name = "Page"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["group_id"]),
            models.Index(fields=["is_blocked"]),
            models.Index(fields=["unblock_date"]),
        ]

    def __str__(self) -> str:
        return f'{self.name}( {self.id})'


class Post(models.Model):
    """ Django model for a post that belong to a page stores and has a like counter."""
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="posts", verbose_name="Page")
    content = models.TextField(max_length=1000, verbose_name="Post content")
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created time")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated time")
    likes_count = models.PositiveSmallIntegerField(default=0, verbose_name="Number of likes")

    class Meta:
        verbose_name_plural = "Posts"
        verbose_name = "Post"
        ordering = ["likes"]
        indexes = [models.Index(fields=["page", "created_at"])]

    def __str__(self) -> str:
        return f'post {self.id}, page {self.page.id}'


class Tag(models.Model):
    """ Django model for a tag that is linked to pages."""
    name = models.CharField(max_length=30, unique=True, verbose_name="tag name")

    class Meta:
        verbose_name_plural = "Tags"
        verbose_name = "Tag"
        ordering = ["name"]

    def __str__(self) -> str:
        return f'{self.name}'


class Followers(models.Model):
    """ Django model stores users that follow a page."""
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="followers", verbose_name="Page")
    user_id = models.CharField(max_length=36, verbose_name="User ID")
    group_id = models.PositiveSmallIntegerField(null=True, verbose_name="Group ID of a user")

    class Meta:
        verbose_name_plural = "Followers"
        verbose_name = "Follower"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["user_id", "page_id"]),
        ]

    def __str__(self) -> str:
        return f'{self.id}'

class Likes(models.Model):
    """ Django model stores users that like a page."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes", verbose_name="Post")
    user_id = models.CharField(max_length=36, verbose_name="User ID")

    class Meta:
        verbose_name_plural = "Likes"
        verbose_name = "Like"
        indexes = [
            models.Index(fields=["post", "user_id"]),
        ]

    def __str__(self) -> str:
        return f'{self.id}'