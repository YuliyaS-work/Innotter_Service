from unittest.mock import patch, MagicMock

from rest_framework.request import Request

from innotter.permissions import AllowAllAuthenticatedUser
from innotter.views import TagDetailAPIView


class TestTagDetailAPIView:
    """
    Tests for TagDetailAPIView.
    These tests check GET and POST methods behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = TagDetailAPIView.as_view()
        self.permission_classes = AllowAllAuthenticatedUser()


    @patch("innotter.views.TagGetSerializer")
    @patch("innotter.views.StandardResultsSetPagination")
    @patch("innotter.views.Tag.objects.all")
    def test_get_success(
            self,
            mock_all_data,
            mock_paginator_class,
            mock_tag_serializer,
            auth_user,
            api_factory,
            tag_data
    ):
        """
        Test checks GET method when tags exist.
        The view should return paginated tag info.
        """
       # Arrange
        request = api_factory.get("/tag/")
        request.auth_user = auth_user

        tag_queryset = MagicMock()
        mock_all_data.return_value = tag_queryset

        paginator = MagicMock()
        mock_paginator_class.return_value = paginator

        paginated_tag_list = MagicMock()
        paginator.paginate_queryset.return_value = paginated_tag_list
        paginator.get_paginated_response.return_value.data = {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [tag_data]
            }

        mock_tag_serializer.return_value.data = [tag_data]

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [tag_data]
        }

        paginator.paginate_queryset.assert_called_once()
        called_tag_list, called_request = paginator.paginate_queryset.call_args[0]
        assert called_tag_list is tag_queryset
        assert isinstance(called_request, Request)

        paginator.get_paginated_response.assert_called_once()
        mock_tag_serializer.assert_called_once()
        mock_tag_serializer.assert_called_once()


    @patch("innotter.views.TagGetSerializer")
    @patch("innotter.views.TagCreateSerializer")
    def test_post_success(
            self,
            mock_create_serializer,
            mock_get_serializer,
            auth_user,
            tag_data,
            api_factory
    ):
        """
        Test checks POST method when data is valid.
        The view should create a new tag and return status 201.
        It checks serializer calls and returned data.
        """
        # Arrange
        payload = {
            "name": "test_tag",
        }

        request = api_factory.post(
            "/tag/",
            payload,
            format="json",
        )
        request.auth_user = auth_user

        create_serializer = MagicMock()
        create_serializer.is_valid.return_value = True

        tag = MagicMock()
        create_serializer.save.return_value = tag
        mock_create_serializer.return_value = create_serializer

        get_serializer = MagicMock()
        get_serializer.data = tag_data
        mock_get_serializer.return_value = get_serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 201
        assert response.data == tag_data

        mock_create_serializer.assert_called_once_with(data=payload)
        create_serializer.is_valid.assert_called_once_with(raise_exception=True)

        create_serializer.save.assert_called_once()

        mock_get_serializer.assert_called_once()