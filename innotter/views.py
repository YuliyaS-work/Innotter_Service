"""
API views for the Innotter service.

This module provides endpoints for:
- feed generation,
- page management (creation, retrieval, modification, blocking, follow/unfollow actions),
- post management (creation, deletion, modification and like/unlike actions),
- tag management (creation, retrieval),
- page image management via S3 (retrieval, upload, confirm, delete).

All endpoints rely on JWT authentication performed by the
middleware.
"""
import logging
from datetime import timedelta
from typing import Any

from celery.worker.control import revoke
from django.db import models
from django.db.models import F
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response

from config import settings
from innotter.exceptions.api_exceptions import ResourceException, LogicException
from innotter.models import Followers, Post, Page, Likes, Tag
from innotter.pagination import StandardResultsSetPagination
from innotter.permissions import AllowAllAuthenticatedUser, IsUserOwner, PageDetailPermission, \
    IsAdminModerator, PostDetailPermission, PageImageDetailPermission
from innotter.s3_service import delete_page_image, generate_page_image_s3_path, create_presigned_post_for_page_image
from innotter.serializers import FeedSerializer, PageCreateUpdateSerializer, PageGetSerializer, PostGetSerializer, \
    PageWithPostsSerializer, FollowersGetSerializer, PostCreateUpdateSerializer, TagCreateSerializer, TagGetSerializer, \
    PageImageUrlSerializer, PageImageUploadSerializer

logger = logging.getLogger(__name__)


def get_object_id(**kwargs) -> int:
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
    permission_classes = [PageDetailPermission]

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
                description="Page number",
                default=1
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of posts per page",
                default=30
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
        request=None,
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
    def patch(self, request: Request, **kwargs: Any)-> Response:
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Updating page, page_id={page_id}")

        page = get_object(Page, page_id)

        self.check_object_permissions(request, page)

        # Update page status
        if page.is_blocked:

            # Remove task if it exists
            if page.task_id:
                revoke(self, page.task_id, terminate=True)
                page.task_id = None

            page.is_blocked = False
            page.unblock_date = None

            page.save(update_fields=["is_blocked", "unblock_date", "task_id"])
        else:
            page.is_blocked = True
            page.unblock_date = timezone.now() + timedelta(minutes=5) # for testing
            # page.unblock_date = timezone.now() + timedelta(hours=24) for production

            page.save(update_fields=["is_blocked", "unblock_date"])

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
    def post(self, request: Request, **kwargs: Any) -> Response:

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


class PageImageDetailAPI(APIView):
    """
    API endpoint for managing a page image stored in S3.
    Handle operations:
    - GET: Retrieve the S3 key of the current page image.
    - POST: Generate a presigned POST for uploading a new image directly to S3.
    - PUT: Confirm the uploaded image by saving its S3 key into the database.
    - DELETE: Remove the image from S3 and clear its key from the database.
    """
    permission_classes = [PageImageDetailPermission]


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the page"
            ),
        ],
        responses={200: PageImageUrlSerializer},
        summary="Get a page image",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return the S3 key (image_url field in Page model) of the page image stored in the database."""

        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Getting a page image, page_id={page_id}")

        page = get_object(Page, page_id)

        if page.image_url is None:
            raise ResourceException("A path to the page image in the database is not exist.")

        logger.info("[PAGE] A page image was loaded successfully")

        return Response(PageImageUrlSerializer({"key": page.image_url}).data, status = 200)


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
        summary="Delete a page image",
    )
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Delete the page image from S3 and remove its key from the database.

        The endpoint:
        - deletes the image object from S3,
        - clears the image_url field in the Page model,
        - returns the updated Page representation.
        """

        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Deleting a page image, page_id={page_id}")

        page = get_object(Page, page_id)

        if page.image_url is None:
            raise ResourceException("A path to the page image in the database is not exist.")

        self.check_object_permissions(request, page)

        delete_page_image(settings.BUCKET_NAME, page.image_url)

        page.image_url = None
        page.save(update_fields=["image_url"])

        logger.info("[PAGE] A page image was deleted")

        return Response(PageGetSerializer(page, context={"request": request}).data, status=200)


    @extend_schema(
        request=None,
        responses={201: PageImageUploadSerializer},
        summary="Upload a new page image",
        description="Upload a new page image by a page owner."
    )
    def post(self, request: Request, **kwargs: Any):
        """
        Generate a presigned POST for uploading a new page image to S3.

        The client must upload the file directly to S3 using these fields.
        The endpoint returns:
        - the S3 upload URL,
        - required form fields,
        - the S3 key where the image will be stored.
        """

        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Uploading a page image to s3 storage, page_id={page_id}")

        page = get_object(Page, page_id)

        self.check_object_permissions(request, page)

        image_s3_path = generate_page_image_s3_path(page_id)

        post = create_presigned_post_for_page_image(
            settings.BUCKET_NAME,
            image_s3_path,
            expiration=3600
        )

        post_response = {
            "key": image_s3_path,
            "url": post["url"],
            "fields": post["fields"]
        }

        logger.info("[PAGE] A page image was sent to s3 storage")

        return Response(post_response, status=201)


    @extend_schema(
        request=PageImageUrlSerializer,
        responses={201: PageGetSerializer},
        summary="Confirm a new page image",
        description="Confirm a new page image by a page owner and save it into the database."
    )
    def put(self, request: Request, **kwargs: Any):
        """
        Confirm the uploaded page image and save its S3 key into the database.

        The client sends the S3 key received from the presigned POST upload.
        The endpoint:
        - deletes the previous image from S3 (if exists),
        - saves the new key into the Page model,
        - returns the updated Page representation.
        """
        page_id = get_object_id(**kwargs)
        logger.info(f"[PAGE] Confirming a new page image, page_id={page_id}")

        page = get_object(Page, page_id)
        self.check_object_permissions(request, page)

        serializer = PageImageUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_image_url = serializer.validated_data["key"]

        if page.image_url:
            delete_page_image(settings.BUCKET_NAME, page.image_url)

        page.image_url = new_image_url
        page.save(update_fields=["image_url"])

        logger.info(f"[PAGE] New image url was saved, page_id={page_id}")

        return Response(PageGetSerializer(page, context={"request": request}).data, status=200)

# =========================================================
# POST
# =========================================================

class PostDetailAPIView(APIView):
    """
    Handle operations on a single post:
    - PATCH: update a post by admin, moderator of the same group or a page owner
    - DELETE: delete a post by admin, moderator of the same group or a page owner
    """
    permission_classes = [PostDetailPermission]

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
        request=None,
        responses={
            200: PostGetSerializer,
            404: OpenApiResponse(description="Post was not found")
        },
        summary="Like/unlike a post",
        description="Like/unlike a post by the authenticated user."
    )
    def patch(self, request: Request, **kwargs: Any)-> Response:
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

# =========================================================
# TAG
# =========================================================

class TagDetailAPIView(APIView):
    """
    Handle operations on a single tag:
    - POST: create a new tag by an any authenticated user.
    - GET: get a tag list with pagination by an any authenticated user.
    """
    permission_classes = [AllowAllAuthenticatedUser]

    @extend_schema(
        request=TagCreateSerializer,
        responses={201: TagGetSerializer},
        summary="Create a new tag",
        description="Create a new tag by an any authenticated user."
    )
    def post(self, request: Request) -> Response:
        """
        Create a new tag by an any authenticated user.
        The endpoint validates input data and stores a new tag in the database.
        Returns a new tag data.
        """
        logger.info("[TAG] Creating a new tag")

        serializer = TagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = serializer.save()

        logger.info("[TAG] A new tag created successfully")

        return Response(TagGetSerializer(tag).data, status=201)


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number",
                default = 1
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of tags per page",
                default = 30
            )
        ],
        responses=PageWithPostsSerializer,
        summary="Get list of tags",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Returns a paginated list of tags (default: 30 tags per page).
        """
        tags = Tag.objects.all()

        paginator= StandardResultsSetPagination()
        paginated_tag_list = paginator.paginate_queryset(tags, request)

        tags_response = paginator.get_paginated_response(
            TagGetSerializer(paginated_tag_list, many=True).data
        ).data

        logger.info("[TAG] A tag list was built successfully")

        return Response(tags_response)