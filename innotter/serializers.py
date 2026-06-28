from rest_framework import serializers

from innotter.models import Post


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