"""
API views for the Innotter service.

page management, feed generation, following/unfollowing operations, and other
user‑driven interactions. All views rely on JWT authentication performed by the
middleware.
"""
import logging
from typing import Any

from django.db import models
from django.db.models import F
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response

from innotter.exceptions.api_exceptions import ResourceException, LogicException
from innotter.models import Followers, Post, Page, Likes
from innotter.pagination import StandardResultsSetPagination
from innotter.permissions import AllowAllAuthenticatedUser, IsUserOwner, PageDetailRemission, \
    IsAdminModerator, PostDetailRemission
from innotter.serializers import FeedSerializer, PageCreateUpdateSerializer, PageGetSerializer, PostGetSerializer, \
    PageWithPostsSerializer, FollowersGetSerializer, PostCreateUpdateSerializer

logger = logging.getLogger(__name__)


def get_object_id(**kwargs) -> int | None:
    """
    Helper function that extracts the object ID (page/post) from request path parameters.
    Raises an error if object is missing.
    """
    for key, value in kwargs.items():
        if key.endswith("_id") and value:
            return value

    logger.error("Resource was not found")
    raise ResourceException("Resource was not found")



def get_object(model: type[models.Model], obj_id: int) -> models.Model:
    """
    Helper function that retrieves a Page/Post instance by its ID.
    Raises a ResourceException if object does not exist.
    """
    try:
        return model.objects.get(pk=obj_id)

    except model.DoesNotExist:
        logger.warning(
            f"[{model.__name__.upper()}] Resource was not found, "
            f"model={model.__name__.upper()}, id={obj_id}"
        )
        raise ResourceException("Resource was not found")


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
        ).values_list("page_id", flat=True)

        post_list = Post.objects.filter(page_id__in=followed_pages, page__is_blocked=False)
        post_list = post_list.select_related("page")    # post list with data page
        post_list = post_list.prefetch_related("page__tags").order_by("-created_at")    # ordered post list with page tags

        serializer = self.serializer_class(post_list, many=True)

        logger.info(f"[FEED] Response ready, user_id={user_id}")

        return Response(serializer.data)


#=========================================================
# PAGE
#=========================================================

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
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Deleting page, page_id={page_id}")

        page = get_object(Page, page_id)

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
        page_id = get_object_id(**kwargs)
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
            PostGetSerializer(paginated_post_list, many=True, context={"request": request}).data
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
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Updating page, page_id={page_id}")

        page = get_object(Page, page_id)

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
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Updating page followers, page_id={page_id}")

        page = get_object(Page, page_id)

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
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Building a followers list of a page, page_id={page_id}")

        page = get_object(Page, page_id)

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
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Updating page, page_id={page_id}")

        page = get_object(Page, page_id)

        self.check_object_permissions(request, page)

        # Update page status
        if page.is_blocked:
            Page.objects.filter(pk=page_id).update(is_blocked=False)
        else:
            Page.objects.filter(pk=page_id).update(is_blocked=True)

        page.refresh_from_db()

        logger.info(f"[PAGE] Page updated successfully, page_id={page_id}")

        return Response(PageGetSerializer(page, context={"request": request}).data, status=200)


class PostCreateAPIView(APIView):
    """
    Create a new post by a page owner.
    The endpoint validates input data and stores a new post in the database.
    Returns a new post data.
    """
    permission_classes = [IsUserOwner]
    serializer_class = PostCreateUpdateSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page to update"
            )
        ],
        request=PostCreateUpdateSerializer,
        responses={201: PostGetSerializer},
        summary="Create a new post",
        description="Create a post by a page owner."
    )
    def post(self, request: Request, **kwargs) -> Response:

        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Creating new post, page_id={page_id}")

        page = get_object(Page, page_id)

        self.check_object_permissions(request, page)

        serializer = PostCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post = serializer.save(
            page_id = page_id
        )

        logger.info("[PAGE] Post created successfully")

        return Response(PostGetSerializer(post, context={"request": request}).data, status=201)

# =========================================================
# POST
# =========================================================

class PostDetailAPIView(APIView):
    """
    Handle operations on a single post:
    - PATCH: update a post by admin, moderator of the same group or a page owner
    - DELETE: delete a post by admin, moderator of the same group or a page owner
    """
    permission_classes = [PostDetailRemission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="post_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Post ID for deleting"
            )
        ],
        responses={
            200: OpenApiResponse(description="Post was deleted successfully"),
            404: OpenApiResponse(description="Post was not found")
        },
        summary="Delete a post",
    )
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Delete the selected post.
        The method checks permissions and removes the page from the database.
        """
        post_id = get_object_id(**kwargs)
        logger.info(f"[POST] Deleting post, post_id={post_id}")

        post = get_object(Post, post_id)

        self.check_object_permissions(request, post.page)

        post.delete()
        logger.info(f"[POST] Post was deleted successfully, post_id={post_id}")

        return Response({"detail": f"Deleted post, post_id={post_id}"})


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="post_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the post to update"
            )
        ],
        request=PostCreateUpdateSerializer,
        responses={
            200: PostGetSerializer,
            404: OpenApiResponse(description="Post was not found")
        },
        summary="Update a post",
        description="Apply partial updates to a post owned by admin, moderator of the same group or a page owner."
    )
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Update post fields for admin, moderator of the same group or a page owner.
        The endpoint applies partial updates to a post.
        Returns the updated post.
        """
        post_id = get_object_id(**kwargs)
        logger.info(f"[POST] Updating page, post_id={post_id}")

        post = get_object(Post, post_id)

        self.check_object_permissions(request, post.page)

        serializer = PostCreateUpdateSerializer(
            post,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        post = serializer.save()

        logger.info("[POST] Post updated successfully")

        return Response(PostGetSerializer(post, context={"request": request}).data, status=200)


class PostLikeUnlikeAPIView(APIView):
    """
    Update like count of the post for the authenticated users.
    Create/delete like in Likes.
    Returns the updated post.
    """
    permission_classes = [AllowAllAuthenticatedUser]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="post_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the post to update"
            )
        ],
        responses={
            200: PostGetSerializer,
            404: OpenApiResponse(description="Post was not found")
        },
        summary="Like/unlike a post",
        description="Like/unlike a post by the authenticated user."
    )
    def patch(self, request: Request, **kwargs)-> Response:
        post_id: int = get_object_id(**kwargs)
        logger.info(f"[POST] Updating post likes, post_id={post_id}")

        post = get_object(Post, post_id)

        self.check_object_permissions(request, post)

        # Check and update like
        like = Likes.objects.filter(post_id=post_id, user_id=request.auth_user["user_id"]).first()
        if like:
            # Decreasing likes count
            like.delete()
            Post.objects.filter(pk=post_id).update(likes_count=F("likes_count") - 1)
            logger.info(f"[POST] Deleted like and updated likes count, post_id={post_id}")
        else:
            # Increasing likes count
            Likes.objects.create(post_id=post_id, user_id=request.auth_user["user_id"])
            Post.objects.filter(pk=post_id).update(likes_count=F("likes_count") + 1)
            logger.info(f"[POST] Created new like and updated likes count, post_id={post_id}")

        post.refresh_from_db()

        return Response(PostGetSerializer(post, context={"request": request}).data, status=200)