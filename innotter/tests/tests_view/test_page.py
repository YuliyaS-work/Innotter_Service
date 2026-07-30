from unittest.mock import MagicMock, patch

from rest_framework.request import Request

from innotter.exceptions.api_exceptions import ResourceException
from innotter.models import Page
from innotter.permissions import PageDetailPermission, AllowAllAuthenticatedUser, IsUserOwner, IsAdminModerator
from innotter.views import PageCreateAPIView, PageDetailAPIView, PageFollowUnfollowAPIView, PageFollowersGetAPIView, \
    PageBlockAPIView, PostCreateAPIView


class TestPageCreateAPIView:
    """
    Test for PageCreateAPIView.
    Test checks POST method behavior.
    """

    def setup_method(self):
        self.view = PageCreateAPIView.as_view()

    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.PageCreateUpdateSerializer")
    def test_post_success(
            self,
            mock_create_update_serializer,
            mock_get_serializer,
            auth_user,
            page_data,
            api_factory
    ):
        """
        Test checks POST method when data is valid.
        The view should create a page and return status 201.
        It checks serializer calls and returned data.
        """
        # Arrange
        payload = {
            "name": "fake name",
            "description": "description",
            "tags": [1]
        }

        request = api_factory.post(
            "/page/",
            payload,
            format="json",
        )
        request.auth_user = auth_user

        create_update_serializer = MagicMock()
        create_update_serializer.is_valid.return_value = True

        page = MagicMock()
        create_update_serializer.save.return_value = page
        mock_create_update_serializer.return_value = create_update_serializer

        get_serializer = MagicMock()
        get_serializer.data = page_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 201
        assert response.data == page_data

        mock_create_update_serializer.assert_called_once_with(data=payload)
        create_update_serializer.is_valid.assert_called_once_with(raise_exception=True)
        create_update_serializer.save.assert_called_once_with(
            user_id=123,
            group_id=1
        )

        mock_get_serializer.assert_called_once()
        args, kwargs = mock_get_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


class TestPageDetailAPIView:
    """
    Tests for PageDetailAPIView.
    These tests check DELETE, GET, and PATCH methods behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PageDetailAPIView.as_view()
        self.permission_classes = PageDetailPermission()

    @patch("innotter.views.PageDetailAPIView.check_object_permissions")
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
        Test checks DELETE method when page exists.
        The view should delete the page and return status 200.
        """
        # Arrange
        request = api_factory.delete("/page/<int:page_id>/")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 200

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()

        mock_check_permissions.assert_called_once()
        called_request, called_page = mock_check_permissions.call_args[0]
        assert isinstance(called_request, Request)
        assert called_page is page

        page.delete.assert_called_once()


    @patch("innotter.views.PostGetSerializer")
    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.StandardResultsSetPagination")
    @patch("innotter.views.Page.objects.prefetch_related")
    @patch("innotter.views.get_object_id")
    def test_get_success(
            self,
            mock_get_object_id,
            mock_get_related_data,
            mock_paginator_class,
            mock_page_serializer,
            mock_post_serializer,
            auth_user,
            post_data,
            page_data,
            api_factory
    ):
        """
        Test checks GET method when page and posts exist.
        The view should return page info and paginated posts.
        """
       # Arrange
        request = api_factory.get("/page/<int:page_id>/")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        related_data = MagicMock()
        mock_get_related_data.return_value.get.return_value = related_data

        post_list = MagicMock()
        related_data.posts.all.return_value = post_list
        post_list.order_by.return_value = post_list

        paginator = MagicMock()
        mock_paginator_class.return_value = paginator

        paginated_post_list = MagicMock()
        paginator.paginate_queryset.return_value = paginated_post_list
        paginator.get_paginated_response.return_value.data = {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [post_data]
            }

        mock_page_serializer.return_value.data = page_data
        mock_post_serializer.return_value.data = [post_data]

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 200
        assert response.data == {
            "page": page_data,
            "posts": {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [post_data]
            }
        }
        mock_get_object_id.assert_called_once()
        mock_get_related_data.return_value.get.assert_called_once_with(pk=page_id)
        related_data.posts.all.assert_called_once()
        post_list.order_by.assert_called_once_with("-created_at")

        paginator.paginate_queryset.assert_called_once()
        called_post_list, called_request = paginator.paginate_queryset.call_args[0]
        assert called_post_list is post_list
        assert isinstance(called_request, Request)

        paginator.get_paginated_response.assert_called_once()
        mock_page_serializer.assert_called_once()
        mock_post_serializer.assert_called_once()


    @patch("innotter.views.Page.objects.prefetch_related")
    @patch("innotter.views.get_object_id")
    def test_get_not_found(
            self,
            mock_get_object_id,
            mock_get_related_data,
            auth_user,
            api_factory
    ):
        """
        Test checks GET method when page is not found.
        The view should return status 404 and raise ResourceException.
        """
        # Arrange
        request = api_factory.get("/page/<int:page_id>/")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        mock_get_related_data.return_value.get.side_effect = Page.DoesNotExist()

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 404

        mock_get_object_id.assert_called_once()
        mock_get_related_data.return_value.get.assert_called_once_with(pk=page_id)


    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.PageCreateUpdateSerializer")
    @patch("innotter.views.PageDetailAPIView.check_object_permissions")
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
            page_data,
            api_factory
    ):
        """
        Test checks PATCH method when data is valid.
        The view should update the page and return status 200.
        """
        # Arrange
        payload = {
            "description": "description",
            "tags": [1]
        }

        request = api_factory.patch(
            "/page/<int:page_id>/",
            payload,
            format="json",
        )
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        create_update_serializer = MagicMock()
        create_update_serializer.is_valid.return_value = True
        create_update_serializer.save.return_value = page
        mock_create_update_serializer.return_value = create_update_serializer

        get_serializer = MagicMock()
        get_serializer.data = page_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == page_data

        mock_create_update_serializer.assert_called_once_with(page, data=payload, partial=True)
        create_update_serializer.is_valid.assert_called_once_with(raise_exception=True)
        create_update_serializer.save.assert_called_once()
        mock_get_serializer.assert_called_once()

        args, kwargs = mock_get_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


class TestPageFollowUnfollowAPIView:
    """
    Tests for PageFollowUnfollowAPIView.
    These tests check PATCH method behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PageFollowUnfollowAPIView.as_view()
        self.permission_classes = AllowAllAuthenticatedUser()

    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.Page.objects.filter")
    @patch("innotter.views.Followers.objects.filter")
    @patch("innotter.views.PageFollowUnfollowAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_patch_unfollow(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_followers_filter,
            mock_page_filter,
            mock_get_serializer,
            api_factory,
            auth_user,
            page_data
    ):
        """
        Test checks PATCH method when page is followed and exists.
        The view should return page info with decreased amount of followers.
        """
        # Arrange
        request = api_factory.patch("/page/<int:page_id>/")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        follower = MagicMock()
        mock_followers_filter.return_value.first.return_value = follower

        page_queryset = MagicMock()
        mock_page_filter.return_value = page_queryset
        page_queryset.update.return_value = page_queryset

        get_serializer = MagicMock()
        get_serializer.data = page_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == page_data

        mock_followers_filter.assert_called_once_with(
            page_id=page_id,
            user_id=auth_user["user_id"],
        )
        mock_page_filter.assert_called_once_with(pk=page_id)

        mock_get_serializer.assert_called_once()
        follower.delete.assert_called_once()
        page.refresh_from_db.assert_called_once()

        args, kwargs = mock_get_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.Page.objects.filter")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_patch_owner(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_page_filter,
            mock_get_serializer,
            api_factory,
            auth_user,
            page_data
    ):
        """
        Test checks PATCH method when page belongs to a user who is an owner.
        The view should raise Logic Error.
        """
        # Arrange
        request = api_factory.patch("/page/<int:page_id>/")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page
        page.user_id = auth_user["user_id"]

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 400
        assert response.data["detail"] == "You cannot follow your own page"

        mock_get_serializer.assert_not_called()

    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.Followers.objects.create")
    @patch("innotter.views.Page.objects.filter")
    @patch("innotter.views.Followers.objects.filter")
    @patch("innotter.views.PageFollowUnfollowAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_patch_follow(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_followers_filter,
            mock_page_filter,
            mock_follower_create,
            mock_get_serializer,
            api_factory,
            auth_user,
            page_data
    ):
        """
        Test checks PATCH method when page is unfollowed and exists.
        The view should return page info with increased amount of followers.
        """
        # Arrange
        request = api_factory.patch("/page/<int:page_id>/follow")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        follower = None

        mock_followers_filter.return_value.first.return_value = follower

        new_follower = MagicMock()
        mock_follower_create.return_value = new_follower

        page_queryset = MagicMock()
        mock_page_filter.return_value = page_queryset
        page_queryset.update.return_value = page_queryset

        get_serializer = MagicMock()
        get_serializer.data = page_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == page_data

        mock_followers_filter.assert_called_once_with(
            page_id=page_id,
            user_id=auth_user["user_id"],
        )

        mock_follower_create.assert_called_once_with(
            page_id=page_id,
            user_id=auth_user["user_id"],
            group_id=auth_user["group_id"],
        )

        mock_page_filter.assert_called_once_with(pk=page_id)
        page_queryset.update.assert_called_once()

        page.refresh_from_db.assert_called_once()

        mock_get_serializer.assert_called_once()
        args, kwargs = mock_get_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


class TestPageFollowersGetAPIView:
    """
    Tests for PageFollowersGetAPIView.
    These tests check GET method behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PageFollowersGetAPIView.as_view()
        self.permission_classes = [IsUserOwner | IsAdminModerator]


    @patch("innotter.views.PageFollowersGetAPIView.check_object_permissions")
    @patch("innotter.views.FollowersGetSerializer")
    @patch("innotter.views.Followers.objects.filter")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_follower_filter,
            mock_follower_serializer,
            mock_check_permissions,
            auth_user,
            api_factory,
            follower_data
    ):
        """
        Test checks GET method when page exists.
        The view should return followers data or empty list.
        """
       # Arrange
        request = api_factory.get("/page/<int:page_id>/followers")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page
        follower_queryset = MagicMock()
        mock_follower_filter.return_value.all.return_value = follower_queryset

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        mock_follower_serializer.return_value.data = follower_data

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 200
        assert response.data == follower_data
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once_with(Page, page_id)
        mock_follower_serializer.assert_called_once()


class TestPageBlockAPIView:
    """
    Tests for PageBlockAPIView.
    These tests check PATCH method behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PageBlockAPIView.as_view()
        self.permission_classes = [IsAdminModerator]


    @patch("innotter.views.PageBlockAPIView.check_object_permissions")
    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_block(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_page_serializer,
            mock_check_permissions,
            auth_user,
            api_factory,
            page_data
    ):
        """
        Test checks PATCH method when page exists.
        The view should return page data with information about blocking.
        """
       # Arrange
        request = api_factory.patch("/page/<int:page_id>/block")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        page.is_blocked = True

        mock_page_serializer.return_value.data = page_data
        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == page_data

        page.save.assert_called_once()

        mock_page_serializer.assert_called_once()
        args, kwargs = mock_page_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


    @patch("innotter.views.PageBlockAPIView.check_object_permissions")
    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_unblock(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_page_serializer,
            mock_check_permissions,
            auth_user,
            api_factory,
            page_data
    ):
        """
        Test checks PATCH method when page exists.
        The view should return page data with information about blocking.
        """
        # Arrange
        request = api_factory.patch("/page/<int:page_id>/block")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        page.is_blocked = False

        mock_page_serializer.return_value.data = page_data
        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == page_data

        page.save.assert_called_once()

        mock_page_serializer.assert_called_once()
        args, kwargs = mock_page_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


class TestPostCreateAPIView:
    """
    Test for PageCreateAPIView.
    Test checks POST method behavior.
    """

    def setup_method(self):
        self.view = PostCreateAPIView.as_view()

    @patch("innotter.views.PostCreateAPIView.check_object_permissions")
    @patch("innotter.views.PostGetSerializer")
    @patch("innotter.views.PostCreateUpdateSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_post_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_create_update_serializer,
            mock_post_serializer,
            mock_check_permissions,
            auth_user,
            post_data,
            api_factory
    ):
        """
        Test checks POST method when data is valid.
        The view should create a post and return status 201.
        It checks serializer calls and returned data.
        """
        # Arrange
        payload = {
            "page": 1,
            "content": "test",
        }

        request = api_factory.post(
            "/page/<int:page_id>/post",
            payload,
            format="json",
        )
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        create_update_serializer = MagicMock()
        create_update_serializer.is_valid.return_value = True

        post = MagicMock()
        create_update_serializer.save.return_value = post
        mock_create_update_serializer.return_value = create_update_serializer

        get_serializer = MagicMock()
        get_serializer.data = post_data
        mock_post_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 201
        assert response.data == post_data

        mock_create_update_serializer.assert_called_once_with(data=payload)
        create_update_serializer.is_valid.assert_called_once_with(raise_exception=True)

        create_update_serializer.save.assert_called_once_with(
            page_id = page_id
        )

        mock_post_serializer.assert_called_once()
        args, kwargs = mock_post_serializer.call_args
        assert args[0] is post
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user