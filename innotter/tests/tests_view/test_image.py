from unittest.mock import patch, MagicMock

from rest_framework.request import Request

from config import settings
from innotter.permissions import PageImageDetailPermission
from innotter.views import PageImageDetailAPIView


class TestPageImageDetailAPIView:
    """
    Tests for PageImageDetailAPIView.
    These tests check DELETE, GET, PUT and POST methods behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = PageImageDetailAPIView.as_view()
        self.permission_classes = PageImageDetailPermission()

    @patch("innotter.views.delete_page_image")
    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.PageImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_delete_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_page_serializer,
            mock_delete_page_image,
            auth_user,
            api_factory,
            page_data
    ):
        """
        Test checks DELETE method when image exists.
        The view should delete the image and return status 200.
        """
        # Arrange
        request = api_factory.delete("/page/<int:page_id>/image")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        page.image_url = "image_url"
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        mock_page_serializer.return_value.data = page_data
        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 200

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()

        mock_check_permissions.assert_called_once()
        mock_delete_page_image.assert_called_once_with(settings.BUCKET_NAME, "image_url")

        mock_page_serializer.assert_called_once()
        args, kwargs = mock_page_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user


    @patch("innotter.views.delete_page_image")
    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.PageImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_delete_not_url(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_page_serializer,
            mock_delete_page_image,
            auth_user,
            api_factory,
            page_data
    ):
        """
        Test checks DELETE method when image url doesn't exist.
        The view should raise ResourceException.
        """
        # Arrange
        request = api_factory.delete("/page/<int:page_id>/image")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        page.image_url = None
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        mock_page_serializer.return_value.data = page_data
        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 404
        assert response.data["detail"] == "A path to the page image in the database is not exist."

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_delete_page_image.assert_not_called()


    @patch("innotter.views.PageImageUrlSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_image_serializer,
            auth_user,
            image_data,
            api_factory
    ):
        """
        Test checks GET method when page image url exists.
        The view should return url info.
        """
       # Arrange
        request = api_factory.get("/page/<int:page_id>/image")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page
        page.image_url = "image_url"

        mock_image_serializer.return_value.data = image_data

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 200
        assert response.data == image_data
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_image_serializer.assert_called_once()


    @patch("innotter.views.PageImageUrlSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_not_image(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_image_serializer,
            auth_user,
            image_data,
            api_factory
    ):
        """
        Test checks GET method when page image url doesn't exist.
        The view should raise ResourceException.
        """
       # Arrange
        request = api_factory.get("/page/<int:page_id>/image")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page
        page.image_url = None

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 404
        assert response.data["detail"] == "A path to the page image in the database is not exist."
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_image_serializer.assert_not_called()


    @patch("innotter.views.create_presigned_post_for_page_image")
    @patch("innotter.views.generate_page_image_s3_path")
    @patch("innotter.views.PageImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_post_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_generate_page_image_s3_path,
            mock_create_presigned_post,
            auth_user,
            image_data,
            api_factory
    ):
        """
        Test checks POST method when presigned_post is formed.
        The view should return post data.
        """
        # Arrange
        request = api_factory.post("/page/<int:page_id>/image")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        mock_generate_page_image_s3_path.return_value = "image_path"
        mock_create_presigned_post.return_value = {
            "key": "image_path",
            "url": "image_url",
            "fields": ["fields1", "fields2"]
        }

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 201
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_generate_page_image_s3_path.assert_called_with(page_id)
        mock_create_presigned_post.assert_called_once_with(
            settings.BUCKET_NAME,
            "image_path",
            expiration=3600
        )
        assert response.data["key"] == "image_path"
        assert response.data["url"] == "image_url"
        assert response.data["fields"] == ["fields1", "fields2"]


    @patch("innotter.views.delete_page_image")
    @patch("innotter.views.PageGetSerializer")
    @patch("innotter.views.PageImageUrlSerializer")
    @patch("innotter.views.PageImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_put_image_exists(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_image_serializer,
            mock_page_serializer,
            mock_delete_page_image,
            auth_user,
            page_data,
            api_factory
    ):
        """
        Test checks PUT method.
        The view should save new image url into the database and
        return updated page data.
        """
       # Arrange
        request = api_factory.put("/page/<int:page_id>/image")
        request.auth_user = auth_user

        page_id = 1
        mock_get_object_id.return_value = page_id
        page = MagicMock()
        mock_get_object.return_value = page

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        image_serializer = MagicMock()
        image_serializer.is_valid.return_value = True

        new_image_url = "new_image_url"
        image_serializer.validated_data.return_value = new_image_url
        mock_image_serializer.return_value = image_serializer

        page.image_url  = "old_image_url"

        mock_page_serializer.return_value.data = page_data

        # Act
        response = self.view(request, page_id)

        # Assert
        assert response.status_code == 200
        assert response.data == page_data

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_image_serializer.assert_called_once()
        mock_delete_page_image.assert_called_once_with(settings.BUCKET_NAME, "old_image_url")
        page.save.assert_called_once()

        mock_page_serializer.assert_called_once()
        args, kwargs = mock_page_serializer.call_args
        assert args[0] is page
        assert "context" in kwargs
        assert "request" in kwargs["context"]
        drf_request = kwargs["context"]["request"]
        assert drf_request.auth_user == auth_user