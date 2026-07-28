from unittest.mock import MagicMock, patch

from rest_framework.request import Request

from innotter.exceptions.api_exceptions import ResourceException
from innotter.permissions import PageDetailPermission
from innotter.views import PageCreateAPIView, PageDetailAPIView


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
        mock_get_related_data.return_value.get.side_effect = ResourceException()

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 404
        assert response.data["detail"] == "Resource is not found"

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