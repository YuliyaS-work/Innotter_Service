from rest_framework import serializers

from innotter.models import Post, Page, Tag


class PageCreateUpdateSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = Tag
        fields = ["id", "name"]


class PageGetSerializer(serializers.ModelSerializer):
    tags = TagGetSerializer(many=True)

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


class PostGetSerializer(serializers.ModelSerializer):

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

class PageWithPostsSerializer(serializers.Serializer):
    page = PageGetSerializer()
    tags = TagGetSerializer(many=True)
    posts = serializers.DictField()


class PageShortSerializer(serializers.ModelSerializer):
    # for feedserializer
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