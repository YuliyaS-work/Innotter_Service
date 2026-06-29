"""
API views for the Innotter service.

page management, feed generation, following/unfollowing operations, and other
user‑driven interactions. All views rely on JWT authentication performed by the
middleware.
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response

from innotter.exceptions.api_exceptions import BaseAPIException
from innotter.models import Followers, Post
from innotter.serializers import FeedSerializer

logger = logging.getLogger(__name__)

class FeedAPIView(APIView):
    """
    Feed API endpoint for retrieving posts from pages followed by the authenticated user.
    """
    serializer_class = FeedSerializer

    def get(self, request):
        user_id = self.request.auth_user["user_id"]
        logger.info(f"[FEED] Request received, user_id={user_id}")

        try:
            followed_pages = Followers.objects.filter(
                user_id=user_id
            ).values_list("page_id")

            posts_list = Post.objects.filter(
                page_id__in=followed_pages
            ).order_by("-created_at")

            serializer = self.serializer_class(posts_list, many=True)

            logger.info(f"[FEED] Response ready, user_id={user_id}")

            return Response(serializer.data)

        except Exception as e:
            logger.error(f"[FEED] Error while building feed, user_id={user_id}, str({e})")

            raise BaseAPIException()