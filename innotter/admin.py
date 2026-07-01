"""
This file contains Django admin configuration for pages, posts, tags, likes and followers.
It defines how these models are shown and searched in the Django admin panel.
"""
from django.contrib import admin

from innotter.models import Page, Post, Followers, Likes, Tag


class PageAdmin(admin.ModelAdmin):
    """Admin class that shows and manages page data in the Django admin."""
    list_display = (
        "id",
        "name",
        "description",
        "user_id",
        "is_blocked",
        "unblock_date",
        "created_at",
        "updated_at",
        "followers_count"
    )
    ordering = ("id", "name", "followers_count")
    readonly_fields = ("followers_count",)
    search_fields = ("name", )


class PostAdmin(admin.ModelAdmin):
    """Admin class that displays posts and their main fields in the Django admin."""
    list_display = (
        "id",
        "get_page_name",
        "content",
        "reply_to",
        "created_at",
        "updated_at",
        "likes_count"
    )
    ordering = ("id", "likes_count",)
    search_fields = ("get_page_name",)
    readonly_fields = ("likes_count",)

    def get_page_name(self, obj):
        """Return page name of a post in the Django admin panel."""
        return obj.page.name
    get_page_name.short_description = "Name page"


class TagAdmin(admin.ModelAdmin):
    """Admin class for viewing and searching tags in the Django admin."""
    list_display = ("id", "name")
    ordering = ("id", "name")
    search_fields = ("name",)


class FollowersAdmin(admin.ModelAdmin):
    """Admin class that shows user subscriptions to pages."""
    list_display = ("id", "user_id", "get_page_id", "get_page_name")
    search_fields = ("page__name",)

    def get_page_id(self, obj):
        """Return followed page ID in the Django admin panel."""
        return obj.page_id
    get_page_id.short_description  = "Page ID"

    def get_page_name(self, obj):
        """Return followed page name in the Django admin panel."""
        return obj.page.name
    get_page_name.short_description = "Name page"


class LikesAdmin(admin.ModelAdmin):
    """Admin class that shows which users liked specific posts."""
    list_display = ("id", "user_id", "get_post_id")
    search_fields = ("page__id",)

    def get_post_id(self, obj):
        """Return liked post ID in the Django admin panel."""
        return obj.post_id
    get_post_id.short_description  = "Post ID"


admin.site.register(Page, PageAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Followers, FollowersAdmin)
admin.site.register(Likes,LikesAdmin)