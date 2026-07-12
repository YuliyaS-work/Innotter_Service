"""
This file contains serializers for pages, posts and tags.
They define how models are converted to JSON and what fields are visible in API responses.
The serializers also control read-only fields and nested tag data.
"""
from rest_framework import serializers

from innotter.models import Post, Page, Tag, Followers


class PageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating a Page."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Page
        fields = [
            "name",
            "description",
            "created_at",
            "tags"
        ]
        read_only_fields = ["created_at"]


class TagGetSerializer(serializers.ModelSerializer):
    """Serializer for returning tag information."""
    class Meta:
        model = Tag
        fields = ["id", "name"]


class PageGetSerializer(serializers.ModelSerializer):
    """Serializer for returning full page information."""
    tags = TagGetSerializer(many=True)
    is_followed = serializers.SerializerMethodField()

    def get_is_followed(self, page):
        request = self.context.get("request")
        return Followers.objects.filter(
            page_id=page.id,
            user_id=request.auth_user["user_id"],
            group_id=request.auth_user["group_id"],
        ).exists()

    class Meta:
        model = Page
        fields = [
            "id",
            "user_id",
            "group_id",
            "name",
            "description",
            "image_url",
            "is_blocked",
            "unblock_date",
            "created_at",
            "updated_at",
            "tags",
            "followers_count",
            "is_followed"
        ]
        read_only_fields = fields


class PostGetSerializer(serializers.ModelSerializer):
    """Serializer for returning post information."""

    class Meta:
        model = Post
        fields = [
            "id",
            "page",
            "content",
            "reply_to",
            "created_at",
            "updated_at",
            "likes_count"
        ]
        read_only_fields = fields

class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new post."""

    class Meta:
        model = Post
        fields = [
            "content",
            "reply_to",
        ]


class PageWithPostsSerializer(serializers.Serializer):
    """Serializer for returning a page together with its tags and posts."""
    page = PageGetSerializer()
    posts = serializers.DictField()


class PageShortSerializer(serializers.ModelSerializer):
    """Short serializer for page data used in feed responses."""
    tags = TagGetSerializer(many=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "tags"
        ]
        read_only_fields = fields


class FeedSerializer(serializers.ModelSerializer):
    """
    Serializer for feed items.
    It includes basic post information and a short page representation.
    """
    page = PageShortSerializer()

    class Meta:
        model = Post
        fields = (
            "id",
            "page",
            "content",
            "created_at",
            "updated_at",
            "likes_count"
        )


class FollowersGetSerializer(serializers.ModelSerializer):
    """Serializer for getting followers from a page."""

    class Meta:
        model = Followers
        fields = ["id", "page", "user_id", "group_id"]