from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError

from innotter.exceptions.api_exceptions import S3StorageError
from innotter.s3_service import generate_image_s3_path, get_s3, delete_image, \
    create_presigned_post


@patch("innotter.s3_service.s3_session")
def test_get_s3(mock_session):
    # Arrange
    fake_client = MagicMock()
    mock_session.client.return_value = fake_client

    # Act
    result = get_s3()

    # Assert
    assert result is fake_client
    mock_session.client.assert_called_once_with("s3")


def test_generate_image_s3_path():
    """
    generate_image_s3_path() should return a valid S3 path for the instance image.
    """
    # Arrange
    page_id = 1

    # Act
    path = generate_image_s3_path(page_id, "Page")
    assert path.startswith("innotter/Page_image/1_")
    assert path.endswith(".webp")


@patch("innotter.s3_service.get_s3")
def test_delete_image_success(mock_get_s3):
    """
    delete_image() should delete the file from S3 when the client succeeds.
    """
    # Arrange
    s3_test = MagicMock()
    mock_get_s3.return_value = s3_test

    # Act
    delete_image("bucket", "key")

    # Assert
    s3_test.delete_object.assert_called_once_with(
        Bucket="bucket",
        Key="key"
    )


@patch("innotter.s3_service.get_s3")
def test_delete_image_client_error(mock_get_s3):
    """
     delete_image() should raise S3StorageError when S3 delete_object fails.
    """
    # Arrange
    mock_get_s3.side_effect =  ClientError(
        {"Error": {}}, "DeleteObject"
    )

    # Act
    with pytest.raises(S3StorageError) as e:
        delete_image("bucket", "key")

    # Assert
    assert e.value.detail == "The image is not deleted"


@patch("innotter.s3_service.get_s3")
def test_create_presigned_post_success(mock_get_s3):
    """
    create_presigned_post() should return a valid presigned POST dict.
    """
    # Arrange
    s3_test = MagicMock()
    mock_get_s3.return_value = s3_test

    s3_test.generate_presigned_post.return_value ={
        "url": "https://s3.aws.test",
        "fields": {"key": "value"}
    }

    # Act
    result = create_presigned_post("bucket", "image_s3_path", "region_mane")

    # Assert
    assert result["url"] == "https://s3.aws.test"
    assert "fields" in result


@patch("innotter.s3_service.get_s3")
def test_create_presigned_post_client_error(mock_get_s3):
    """
    create_presigned_post() should raise S3StorageError when S3 fails.
    """
    # Arrange
    s3_test = MagicMock()
    mock_get_s3.return_value = s3_test
    s3_test.generate_presigned_post.side_effect = ClientError (
        {"Error": {"Code": "500", "Message": "fail"}}, "GeneratePresignedPost"
    )

    # Act
    with pytest.raises(S3StorageError) as e:
        create_presigned_post("bucket", "image_s3_path", "region_mane")

    # Assert
    assert e.value.detail == "Presigned post is not generated"


def test_create_presigned_post_empty_path():
    """
    create_presigned_post() should raise S3StorageError when image_s3_path is missing.
    """
    # Act
    with pytest.raises(S3StorageError) as e:
        create_presigned_post("bucket", None, "region_mane")

    # Assert
    assert e.value.detail == "A path to the image in the database is not exist."