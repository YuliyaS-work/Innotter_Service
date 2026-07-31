from unittest.mock import patch, MagicMock

from rest_framework.request import Request

from innotter.permissions import PostDetailPermission, AllowAllAuthenticatedUser
from innotter.views import PostDetailAPIView, PostLikeUnlikeAPIView


class TestPostDetailAPIView:
    """
    Tests for PostDetailAPIView.
    These tests check DELETE and PATCH methods behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PostDetailAPIView.as_view()
        self.permission_classes = PostDetailPermission()


    @patch("innotter.views.PostDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_delete_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            auth_user,
            api_factory
    ):
        """
        Test checks DELETE method when post exists.
        The view should delete the post and return status 200.
        """
        # Arrange
        request = api_factory.delete("/post/<int:post_id>/")
        request.auth_user = auth_user

        post_id = 1
        mock_get_object_id.return_value = (post_id, "Post")
        post = MagicMock()
        mock_get_object.return_value = post

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        # Act
        response = self.view(request, post.page)

        # Assert
        assert response.status_code == 200

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()

        mock_check_permissions.assert_called_once()
        called_request, called_post = mock_check_permissions.call_args[0]
        assert isinstance(called_request, Request)
        assert called_post is post.page

        post.delete.assert_called_once()


    @patch("innotter.views.PostGetSerializer")
    @patch("innotter.views.PostCreateUpdateSerializer")
    @patch("innotter.views.PostDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_patch_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_create_update_serializer,
            mock_get_serializer,
            auth_user,
            post_data,
            api_factory
    ):
        """
        Test checks PATCH method when data is valid.
        The view should update the post and return status 200.
        """
        # Arrange
        payload = {
            "content": "new_text",
        }

        request = api_factory.patch(
            "/post/<int:post_id>/",
            payload,
            format="json",
        )
        request.auth_user = auth_user

        post_id = 1
        mock_get_object_id.return_value = (post_id, "Post")
        post = MagicMock()
        mock_get_object.return_value = post

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        create_update_serializer = MagicMock()
        create_update_serializer.is_valid.return_value = True
        create_update_serializer.save.return_value = post
        mock_create_update_serializer.return_value = create_update_serializer

        get_serializer = MagicMock()
        get_serializer.data = post_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request, post_id)

        # Assert
        assert response.status_code == 200
        assert response.data == post_data

        mock_create_update_serializer.assert_called_once_with(post, data=payload, partial=True)
        create_update_serializer.is_valid.assert_called_once_with(raise_exception=True)
        create_update_serializer.save.assert_called_once()
        mock_get_serializer.assert_called_once()

        args, kwargs = mock_get_serializer.call_args
        assert args[0] is post
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


class TestPostLikeUnlikeAPIView:
    """
    Tests for PostLikeUnlikeAPIView.
    These tests check PATCH method behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PostLikeUnlikeAPIView.as_view()
        self.permission_classes = AllowAllAuthenticatedUser()


    @patch("innotter.views.PostGetSerializer")
    @patch("innotter.views.Post.objects.filter")
    @patch("innotter.views.Likes.objects.filter")
    @patch("innotter.views.PostLikeUnlikeAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_patch_unlike(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_likes_filter,
            mock_post_filter,
            mock_get_serializer,
            api_factory,
            auth_user,
            post_data
    ):
        """
        Test checks PATCH method when post is liked and exists.
        The view should return post info with decreased amount of likes.
        """
        # Arrange
        request = api_factory.patch("/page/<int:page_id>/")
        request.auth_user = auth_user

        post_id = 1
        mock_get_object_id.return_value = (post_id, "Post")
        post = MagicMock()
        mock_get_object.return_value = post

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        like = MagicMock()
        mock_likes_filter.return_value.first.return_value = like

        post_queryset = MagicMock()
        mock_post_filter.return_value = post_queryset
        post_queryset.update.return_value = post_queryset

        get_serializer = MagicMock()
        get_serializer.data = post_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == post_data

        mock_likes_filter.assert_called_once_with(
            post_id=post_id,
            user_id=auth_user["user_id"],
        )
        mock_post_filter.assert_called_once_with(pk=post_id)

        mock_get_serializer.assert_called_once()
        like.delete.assert_called_once()
        post.refresh_from_db.assert_called_once()

        args, kwargs = mock_get_serializer.call_args
        assert args[0] is post
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


    @patch("innotter.views.Likes.objects.create")
    @patch("innotter.views.PostGetSerializer")
    @patch("innotter.views.Post.objects.filter")
    @patch("innotter.views.Likes.objects.filter")
    @patch("innotter.views.PostLikeUnlikeAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_patch_like(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_likes_filter,
            mock_post_filter,
            mock_get_serializer,
            mock_like_create,
            api_factory,
            auth_user,
            post_data
    ):
        """
        Test checks PATCH method when post is unliked and exists.
        The view should return post info with increased amount of likes.
        """
        # Arrange
        request = api_factory.patch("/page/<int:page_id>/")
        request.auth_user = auth_user

        post_id = 1
        mock_get_object_id.return_value = (post_id, "Post")
        post = MagicMock()
        mock_get_object.return_value = post

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        like = None
        mock_likes_filter.return_value.first.return_value = like

        post_queryset = MagicMock()
        mock_post_filter.return_value = post_queryset
        post_queryset.update.return_value = post_queryset

        get_serializer = MagicMock()
        get_serializer.data = post_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == post_data

        mock_likes_filter.assert_called_once_with(
            post_id=post_id,
            user_id=auth_user["user_id"],
        )
        mock_like_create.assert_called_once_with(
            post_id=post_id,
            user_id=auth_user["user_id"],
        )
        mock_post_filter.assert_called_once_with(pk=post_id)

        mock_get_serializer.assert_called_once()
        post.refresh_from_db.assert_called_once()

        args, kwargs = mock_get_serializer.call_args
        assert args[0] is post
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user