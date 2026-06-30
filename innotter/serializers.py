from rest_framework import serializers

from innotter.models import Post, Page, Tag


class FeedSerializer(serializers.ModelSerializer):
    page_name = serializers.CharField(source="page.name")
    page_tags = serializers.StringRelatedField(source="page.tags", many=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "page",
            "content",
            "created_at",
            "updated_at",
            "likes_count",
            "page_name",
            "page_tags"
        )

class PageCreateSerializer(serializers.ModelSerializer):
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


class PageGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "description",
            "image_url",
            "is_blocked",
            "unblock_date",
            "created_at",
            "updated_at",
            "tags",
            "followers_count"
        ]
        read_only_fields = fields