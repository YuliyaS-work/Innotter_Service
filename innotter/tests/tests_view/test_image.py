from unittest.mock import patch, MagicMock

import pytest

from config import settings
from innotter.models import Page, Post
from innotter.permissions import ImageDetailPermission
from innotter.serializers import PostGetSerializer, PageGetSerializer
from innotter.views import ImageDetailAPIView, SERIALIZER_MAP


class TestImageDetailAPIView:
    """
    Tests for ImageDetailAPIView.
    These tests check DELETE, GET, PUT and POST methods behavior.
    They verify permissions, object loading, and responses.
    """

    def setup_method(self):
        self.view = ImageDetailAPIView.as_view()
        self.permission_classes = ImageDetailPermission()


    @pytest.mark.parametrize("entity,model,serializer", [
        ("Page", Page, PageGetSerializer),
        ("Post", Post, PostGetSerializer),
    ])
    @patch("innotter.views.delete_image")
    @patch("innotter.views.ImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    @patch.dict("innotter.views.SERIALIZER_MAP",{},clear=True)
    def test_delete_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_delete_image,
            entity,
            model,
            serializer,
            auth_user,
            api_factory
    ):
        """
        Test checks DELETE method when image exists.
        The view should delete the image and return status 200.
        """
        # Arrange
        instance_id = 1

        serializer_instance = MagicMock()
        serializer_instance.data = {"id": instance_id, "image_url": None}

        SERIALIZER_MAP[entity] = lambda obj, context: serializer_instance

        request = api_factory.delete("/{entity.lower()}/{instance_id}/image")
        request.auth_user = auth_user

        mock_get_object_id.return_value = (instance_id, entity)

        instance = MagicMock(spec=model)
        instance.id = instance_id
        instance.image_url = "image_url.webp"
        mock_get_object.return_value = instance

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        # Act
        response = self.view(request, instance_id)

        # Assert
        assert response.status_code == 200

        assert instance.image_url is None
        instance.save.assert_called_once_with(update_fields=["image_url"])
        assert response.data == serializer_instance.data

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once_with(model, instance_id)
        mock_check_permissions.assert_called_once()
        mock_delete_image.assert_called_once_with(settings.BUCKET_NAME, "image_url.webp")



    @pytest.mark.parametrize("entity,model,serializer", [
        ("Page", Page, PageGetSerializer),
        ("Post", Post, PostGetSerializer),
    ])
    @patch("innotter.views.delete_image")
    @patch("innotter.views.ImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    @patch.dict("innotter.views.SERIALIZER_MAP",{},clear=True)
    def test_delete_not_url(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_delete_image,
            entity,
            model,
            serializer,
            auth_user,
            api_factory
    ):
        """
        Test checks DELETE method when image url doesn't exist.
        The view should raise ResourceException.
        """
        # Arrange
        instance_id = 1

        serializer_instance = MagicMock()
        serializer_instance.data = {"id": instance_id, "image_url": None}

        SERIALIZER_MAP[entity] = lambda obj, context: serializer_instance

        request = api_factory.delete("/{entity.lower()}/{instance_id}/image")
        request.auth_user = auth_user

        mock_get_object_id.return_value = (instance_id, entity)

        instance = MagicMock(spec=model)
        instance.id = instance_id
        instance.image_url = None
        mock_get_object.return_value = instance

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        # Act
        response = self.view(request, instance_id)

        # Assert
        assert response.status_code == 404
        assert response.data["detail"] == "A path to the instance image in the database is not exist."

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_delete_image.assert_not_called()


    @pytest.mark.parametrize("entity,model", [
        ("Page", Page),
        ("Post", Post),
    ])
    @patch("innotter.views.ImageUrlSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_image_serializer,
            auth_user,
            image_data,
            api_factory,
            entity,
            model,
    ):
        """
        Test checks GET method when image url exists.
        The view should return url info.
        """
       # Arrange
        instance_id = 1

        request = api_factory.get("/{entity.lower()}/{instance_id}/image")
        request.auth_user = auth_user

        mock_get_object_id.return_value = (instance_id, entity)

        instance = MagicMock(spec=model)
        instance.id = instance_id
        instance.image_url = "image_url"
        mock_get_object.return_value = instance

        mock_image_serializer.return_value.data = image_data

        # Act
        response = self.view(request, instance_id)

        # Assert
        assert response.status_code == 200
        assert response.data == image_data
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_image_serializer.assert_called_once()



    @pytest.mark.parametrize("entity,model", [
        ("Page", Page),
        ("Post", Post),
    ])
    @patch("innotter.views.ImageUrlSerializer")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_get_not_image(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_image_serializer,
            auth_user,
            image_data,
            api_factory,
            entity,
            model,
    ):
        """
        Test checks GET method when image url doesn't exist.
        The view should raise ResourceException.
        """
       # Arrange
        instance_id = 1

        request = api_factory.get("/{entity.lower()}/{instance_id}/image")
        request.auth_user = auth_user

        mock_get_object_id.return_value = (instance_id, entity)

        instance = MagicMock(spec=model)
        instance.id = instance_id
        instance.image_url = None
        mock_get_object.return_value = instance
        # Act
        response = self.view(request, instance_id)

        # Assert
        assert response.status_code == 404
        assert response.data["detail"] == "A path to the instance image in the database is not exist."
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_image_serializer.assert_not_called()


    @pytest.mark.parametrize("entity,model", [
        ("Page", Page),
        ("Post", Post),
    ])
    @patch("innotter.views.create_presigned_post")
    @patch("innotter.views.generate_image_s3_path")
    @patch("innotter.views.ImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    def test_post_success(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_generate_image_s3_path,
            mock_create_presigned_post,
            auth_user,
            image_data,
            api_factory,
            entity,
            model,
    ):
        """
        Test checks POST method when presigned_post is formed.
        The view should return post data.
        """
        # Arrange
        instance_id = 1

        request = api_factory.post("/{entity.lower()}/{instance_id}/image")
        request.auth_user = auth_user

        mock_get_object_id.return_value = (instance_id, entity)

        instance = MagicMock(spec=model)
        mock_get_object.return_value = instance

        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        mock_generate_image_s3_path.return_value = "image_path"
        mock_create_presigned_post.return_value = {
            "key": "image_path",
            "url": "image_url",
            "fields": ["fields1", "fields2"]
        }

        # Act
        response = self.view(request, instance_id)

        # Assert
        assert response.status_code == 201
        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_generate_image_s3_path.assert_called_with(instance_id, entity)
        mock_create_presigned_post.assert_called_once_with(
            settings.BUCKET_NAME,
            "image_path",
            expiration=3600
        )
        assert response.data["key"] == "image_path"
        assert response.data["url"] == "image_url"
        assert response.data["fields"] == ["fields1", "fields2"]


    @pytest.mark.parametrize("entity,model,serializer", [
        ("Page", Page, PageGetSerializer),
        ("Post", Post, PostGetSerializer),
    ])
    @patch("innotter.views.delete_image")
    @patch("innotter.views.ImageUrlSerializer")
    @patch("innotter.views.ImageDetailAPIView.check_object_permissions")
    @patch("innotter.views.get_object")
    @patch("innotter.views.get_object_id")
    @patch.dict("innotter.views.SERIALIZER_MAP",{},clear=True)
    def test_put_image_exists(
            self,
            mock_get_object_id,
            mock_get_object,
            mock_check_permissions,
            mock_image_serializer,
            mock_delete_image,
            auth_user,
            api_factory,
            entity,
            model,
            serializer,
    ):
        """
        Test checks PUT method.
        The view should save new image url into the database and
        return updated page data.
        """
       # Arrange
        instance_id = 1

        serializer_instance = MagicMock()
        serializer_instance.data = {"id": instance_id, "image_url": None}

        SERIALIZER_MAP[entity] = lambda obj, context: serializer_instance

        request = api_factory.put("/{entity.lower()}/{instance_id}/image")
        request.auth_user = auth_user

        mock_get_object_id.return_value = (instance_id, entity)

        instance = MagicMock(spec=model)
        instance.id = instance_id
        instance.image_url = "image_url.webp"
        mock_get_object.return_value = instance


        permission_classes = MagicMock()
        permission_classes.return_value = True
        mock_check_permissions.return_value = None

        image_serializer = MagicMock()
        image_serializer.is_valid.return_value = True

        new_image_url = "new_image_url"
        image_serializer.validated_data.return_value = new_image_url
        mock_image_serializer.return_value = image_serializer

        instance.image_url  = "old_image_url"


        # Act
        response = self.view(request, instance_id)

        # Assert
        assert response.status_code == 200

        mock_get_object_id.assert_called_once()
        mock_get_object.assert_called_once()
        mock_image_serializer.assert_called_once()
        mock_delete_image.assert_called_once_with(settings.BUCKET_NAME, "old_image_url")
        instance.save.assert_called_once_with(update_fields=["image_url"])
        assert response.data == serializer_instance.data