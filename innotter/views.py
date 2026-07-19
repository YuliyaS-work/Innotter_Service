"""
API views for the Innotter service.

page management, feed generation, following/unfollowing operations, and other
user‑driven interactions. All views rely on JWT authentication performed by the
middleware.
"""
import logging
from typing import Any

from django.db.models import F
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response

from innotter.exceptions.api_exceptions import BaseAPIException, ResourceException, LogicException
from innotter.models import Followers, Post, Page
from innotter.pagination import StandardResultsSetPagination
from innotter.permissions import AllowAllAuthenticatedUser, IsUserOwner, PageDetailRemission, \
    IsAdminModerator
from innotter.serializers import FeedSerializer, PageCreateUpdateSerializer, PageGetSerializer, PostGetSerializer, \
    PageWithPostsSerializer, FollowersGetSerializer, PostCreateSerializer

logger = logging.getLogger(__name__)

#=========================================================
# FEED
#=========================================================

class FeedAPIView(APIView):
    """
    Return a feed of posts from pages followed by the authenticated user.
    The endpoint collects posts from all followed pages, orders them by creation time,
    and returns them as a JSON list.
    """
    permission_classes = [AllowAllAuthenticatedUser]
    serializer_class = FeedSerializer

    @extend_schema(
        responses=FeedSerializer,
        summary="Get user feed",
        description="Return posts from pages followed by the authenticated user."
    )

    def get(self, request: Request) -> Response:
        user_id: int = self.request.auth_user["user_id"]
        logger.info(f"[FEED] Request received, user_id={user_id}")

        followed_pages = Followers.objects.filter(
            user_id=user_id
        ).values_list("page_id")

        post_list = Post.objects.filter(page_id__in=followed_pages)
        post_list = post_list.select_related("page")    # post list with data page
        post_list = post_list.prefetch_related("page__tags").order_by("-created_at")    # ordered post list with page tags

        serializer = self.serializer_class(post_list, many=True)

        logger.info(f"[FEED] Response ready, user_id={user_id}")

        return Response(serializer.data)


#=========================================================
# PAGE
#=========================================================

def get_page_id(**kwargs) -> int | None:
    """
    Helper function that extracts the page_id from request path parameters.
    Raises an error if page_id is missing.
    """
    page_id: int | None = kwargs.get("page_id", None)

    if not page_id:
        logger.error("[PAGE] Page was not found")
        raise ResourceException("Page was not found")

    return page_id


def get_page(page_id: int):
    """
    Helper function that retrieves a Page instance by its ID.
    Raises a ResourceException if the page does not exist.
    """
    try:
        return Page.objects.get(pk=page_id)

    except Page.DoesNotExist:
        logger.error("[PAGE] Page was not found")
        raise ResourceException("Page was not found")


class PageCreateAPIView(APIView):
    """
    Create a new page for the authenticated user.
    The endpoint validates input data and stores a new page in the database.
    Returns a new page.
    """
    permission_classes = [AllowAllAuthenticatedUser]

    @extend_schema(
        request=PageCreateUpdateSerializer,
        responses={201: PageGetSerializer},
        summary="Create a new page",
        description="Create a page for the authenticated user."
    )

    def post(self, request: Request) -> Response:
        logger.info("[PAGE] Creating new page")

        serializer = PageCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        page = serializer.save(
            user_id=request.auth_user["user_id"],
            group_id=request.auth_user["group_id"]
        )

        logger.info("[PAGE] Page created successfully")

        return Response(PageGetSerializer(page, context={"request": request}).data, status=201)


class PageDetailAPIView(APIView):
    """
    Handle operations on a single page:
    - GET: page with its posts and related tags by any authenticated user
    - PATCH: update a page by a page owner
    - DELETE: delete a page by admin, moderator of the same group or a page owner
    """
    permission_classes = [PageDetailRemission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Page ID for deleting"
            )
        ],
        responses={
            200: OpenApiResponse(description="Page was deleted successfully"),
            404: OpenApiResponse(description="Page was not found")
        },
        summary="Delete a page",
    )
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Delete the selected page.
        The method checks permissions and removes the page from the database.
        """
        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Deleting page, page_id={page_id}")

        page = get_page(page_id)

        self.check_object_permissions(request, page)

        page.delete()

        logger.info(f"[PAGE] Page was deleted successfully, page_id={page_id}")

        return Response({"detail": f"Deleted page, page_id={page_id}"})


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number"
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of posts per page"
            )
        ],
        responses=PageWithPostsSerializer,
        summary="Get posts of a page",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Return page info, related tags and paginated posts.
        The method builds a combined response with page data and posts.
        """
        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Building a post list of a page, page_id={page_id}")

        try:
            page: Page = Page.objects.prefetch_related("posts", "tags").get(pk=page_id)
        except Page.DoesNotExist:
            logger.error("[PAGE] Page was not found")
            raise ResourceException("Page was not found")

        post_list = page.posts.all().order_by("-created_at")

        paginator= StandardResultsSetPagination()
        paginated_post_list = paginator.paginate_queryset(post_list, request)

        post_response = paginator.get_paginated_response(
            PostGetSerializer(paginated_post_list, many=True).data
        ).data

        # data tags are included in "page"
        data_response = {
            "page": PageGetSerializer(page, context={"request": request}).data,
            "posts": post_response
        }

        logger.info(f"[PAGE] Post list was built successfully, page_id={page_id}")

        return Response(data_response)


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page to update"
            )
        ],
        request=PageCreateUpdateSerializer,
        responses={
            200: PageGetSerializer,
            404: OpenApiResponse(description="Page was not found")
        },
        summary="Update a page",
        description="Apply partial updates to a page owned by the authenticated user."
    )
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Update page fields for the authenticated page owner.
        The endpoint applies partial updates to a page.
        Returns the updated page.
        """
        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Updating page, page_id={page_id}")

        page = get_page(page_id)

        self.check_object_permissions(request, page)

        serializer = PageCreateUpdateSerializer(
            page,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        page = serializer.save()

        logger.info("[PAGE] Page updated successfully")

        return Response(PageGetSerializer(page, context={"request": request}).data, status=200)


class PageFollowUnfollowAPIView(APIView):
    """
    Update follower count of the page for the authenticated page owner.
    Create/delete a follower in Followers.
    Returns the updated page.
    """
    permission_classes = [AllowAllAuthenticatedUser]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page to update"
            )
        ],
        responses={
            200: PageGetSerializer,
            404: OpenApiResponse(description="Page was not found")
        },
        summary="Follow/unfollow a page",
        description="Follow/unfollow a page by the authenticated user."
    )
    def patch(self, request: Request, **kwargs)-> Response:
        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Updating page followers, page_id={page_id}")

        page = get_page(page_id)

        # Check a page owner
        if page.user_id == request.auth_user["user_id"]:
            logger.error(f"[PAGE] You cannot follow your own page, page_id={page_id}")
            raise LogicException("You cannot follow your own page")

        self.check_object_permissions(request, page)

        follower = Followers.objects.filter(page_id=page_id, user_id=request.auth_user["user_id"]).first()

        if follower:
            # Decreasing follower count
            follower.delete()
            Page.objects.filter(pk=page_id).update(followers_count=F("followers_count") - 1)
            logger.info(f"[PAGE] Deleted a follower, page_id={page_id}")
        else:
            # Increasing follower count
            Followers.objects.create(
                page_id=page_id,
                user_id=request.auth_user["user_id"],
                group_id=request.auth_user["group_id"]
            )
            Page.objects.filter(pk=page_id).update(followers_count=F("followers_count") + 1)
            logger.info(f"[PAGE] Created a new follower, page_id={page_id}")

        page.refresh_from_db()

        return Response(PageGetSerializer(page, context={"request": request}).data, status=200)


class PageFollowersGetAPIView(APIView):
    """
    Returns the list of page followers according to the authenticated user's role.
    ADMIN: returns all followers.
    MODERATOR: returns followers from the page with user ID of the same group.
    USER: returns followers only if they own the page.
    """
    permission_classes = [IsUserOwner | IsAdminModerator]
    serializer_class = FollowersGetSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page"
            ),
        ],
        responses={200: FollowersGetSerializer},
        summary="Get followers of a page",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Building a followers list of a page, page_id={page_id}")

        page = get_page(page_id)

        self.check_object_permissions(request, page)

        followers = Followers.objects.filter(page_id=page_id).all()
        logger.info(f"[PAGE] Followers list was built successfully, page_id={page_id}")
        return Response(FollowersGetSerializer(followers, many=True).data, status=200)


class PageBlockAPIView(APIView):
    """
    Updates the page status according to the authenticated user's role.
    ADMIN can block/unblock all pages.
    MODERATOR  can block/unblock pages created by users with the same group ID.
    Returns the updated page data.
    """
    permission_classes = [IsAdminModerator]
    serializer_class = PageGetSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page to update"
            )
        ],
        request = None,
        responses={
            200: PageGetSerializer,
            404: OpenApiResponse(description="Page was not found")
        },
        summary="Update a page status",
        description="Update a page status by admin or moderator with the same group like owner."
    )
    def patch(self, request: Request, **kwargs)-> Response:
        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Updating page, page_id={page_id}")

        page = get_page(page_id)

        self.check_object_permissions(request, page)

        # Update page status
        if page.is_blocked:
            page.is_blocked = False
            page.save(update_fields=["is_blocked"])
        else:
            page.is_blocked = True
            page.save(update_fields=["is_blocked"])

        logger.info(f"[PAGE] Page updated successfully, page_id={page_id}")

        return Response(PageGetSerializer(page, context={"request": request}).data, status=200)


class PostCreateAPIView(APIView):
    """
    Create a new post by a page owner.
    The endpoint validates input data and stores a new post in the database.
    Returns a new post data.
    """
    permission_classes = [IsUserOwner]
    serializer_class = PostCreateSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page to update"
            )
        ],
        request=PostCreateSerializer,
        responses={201: PostGetSerializer},
        summary="Create a new post",
        description="Create a post by a page owner."
    )
    def post(self, request: Request, **kwargs) -> Response:

        page_id = get_page_id(**kwargs)
        logger.info(f"[PAGE] Creating new post, page_id={page_id}")

        page = get_page(page_id)

        self.check_object_permissions(request, page)

        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post = serializer.save(
            page_id = page_id
        )

        logger.info("[PAGE] Post created successfully")

        return Response(PostGetSerializer(post).data, status=201)