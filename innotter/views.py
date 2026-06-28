from rest_framework import generics

from innotter.models import Followers, Post
from innotter.serializers import FeedSerializer


class FeedListAPIView(generics.ListAPIView):
    serializer_class = FeedSerializer

    def get_queryset(self):
        user_id = self.request.auth_user["user_id"]
        followed_pages = Followers.objects.filter(user_id=user_id).values_list("page_id")
        posts_list = Post.objects.filter(page_id__in=followed_pages).order_by("-created_at")
        return posts_list