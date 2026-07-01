"""
API views for the Innotter service.

page management, feed generation, following/unfollowing operations, and other
user‑driven interactions. All views rely on JWT authentication performed by the
middleware.
"""
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response

from innotter.exceptions.api_exceptions import BaseAPIException, ResourceException
from innotter.models import Followers, Post, Page
from innotter.pagination import StandardResultsSetPagination
from innotter.permissions import AllowAllAuthenticatedUser, AllowAllRoles
from innotter.serializers import FeedSerializer, PageCreateSerializer, PageGetSerializer, PostGetSerializer, \
    PageWithPostsSerializer, TagGetSerializer

logger = logging.getLogger(__name__)

class FeedAPIView(APIView):
    """
    Feed API endpoint for retrieving posts from pages followed by the authenticated user.
    """
    permission_classes = [AllowAllAuthenticatedUser]
    serializer_class = FeedSerializer

    def get(self, request):
        user_id = self.request.auth_user["user_id"]
        logger.info(f"[FEED] Request received, user_id={user_id}")

        try:
            followed_pages = Followers.objects.filter(
                user_id=user_id
            ).values_list("page_id")

            post_list = Post.objects.filter(page_id__in=followed_pages)
            post_list = post_list.select_related("page")    # post list with data page
            post_list = post_list.prefetch_related("page__tags").order_by("-created_at")    # ordered post list with page tags

            serializer = self.serializer_class(post_list, many=True)

            logger.info(f"[FEED] Response ready, user_id={user_id}")

            return Response(serializer.data)

        except Exception as e:
            logger.error(f"[FEED] Error while building feed, user_id={user_id}, str({e})")

            raise BaseAPIException()


class PageCreateAPIView(APIView):
    permission_classes = [AllowAllAuthenticatedUser]

    @swagger_auto_schema(
        request_body=PageCreateSerializer,
        responses={201: PageGetSerializer}
    )

    def post(self, request):
        logger.info(f"[PAGE] Creating new page")
        serializer = PageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            page = serializer.save(
                user_id=request.auth_user["user_id"],
                group_id=request.auth_user["group_id"]
            )

            logger.info(f"[PAGE] Page created successfully")

            return Response(PageGetSerializer(page).data, status=201)
        except Exception as e:
            logger.error(f"[PAGE] Page was not created, srt({e})")
            raise BaseAPIException()



class PageDeleteAPIView(APIView):
    permission_classes = [AllowAllRoles]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name="page_id",
                in_=openapi.IN_PATH,
                description="Page ID for deleting",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response("Page was deleted successfully"),
            404: openapi.Response("Page was not found")
        }
    )

    def delete(self, request, *args, **kwargs):
        page_id = kwargs.get("page_id", None)
        logger.info(f"[PAGE] Deleting page, page_id={page_id}")

        if not page_id:
            logger.error(f"[PAGE] Page was not found")
            raise ResourceException("Page was not found")

        try:
            instance = Page.objects.get(pk=page_id)
        except Page.DoesNotExist:
            logger.error(f"[PAGE] Page was not found")
            raise ResourceException("Page was not found")

        self.check_object_permissions(request, instance)

        try:
            instance.delete()
            logger.info(f"[PAGE] Page was deleted successfully, page_id={page_id}")

        except Exception as e:
            logger.error(f"[PAGE] Page was not deleted, srt({e})")
            raise BaseAPIException()

        return Response({"detail": f"Deleted page, page_id={page_id}"})


class PagePostsGetAPIView(APIView):
    permission_classes = [AllowAllAuthenticatedUser]
    serializer_class = PageWithPostsSerializer
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name="page",
                in_=openapi.IN_QUERY,
                description="Page",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="page_size",
                in_=openapi.IN_QUERY,
                description="Number of posts",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ]
    )

    def get(self, request, *args, **kwargs):
        page_id = kwargs.get("page_id", None)
        logger.info(f"[PAGE] Building a post list of a page, page_id={page_id}")

        if not page_id:
            logger.error(f"[PAGE] Page was not found")
            raise ResourceException("Page was not found")

        try:
            page = Page.objects.prefetch_related("posts", "tags").get(pk=page_id)
            post_list = page.posts.all().order_by("-created_at")

            paginator = self.pagination_class()
            paginated_post_list = paginator.paginate_queryset(post_list, request)

            post_response = paginator.get_paginated_response(
                PostGetSerializer(paginated_post_list, many=True).data
            ).data
            data_response = {
                "page": PageGetSerializer(page).data,
                "tags": TagGetSerializer(page.tags.all(), many=True).data,
                "posts": post_response
            }

            logger.info(f"[PAGE] Post list was built successfully, page_id={page_id}")
            return Response(data_response)

        except Page.DoesNotExist:
            logger.error(f"[PAGE] Page was not found")
            raise ResourceException("Page was not found")

        except Exception as e:
            logger.error(f"[PAGE] Error while building post list, page_id={page_id}, srt({e})")
            raise BaseAPIException()