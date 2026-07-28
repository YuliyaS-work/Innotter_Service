from unittest.mock import MagicMock

import pytest

from innotter.exceptions.api_exceptions import ResourceException
from innotter.views import get_object_id, get_object


def test_get_object_id_success():
    """ This test check that get_object_id() should return the correct item_id value."""
    # Arrange
    parameter = {"item_id": "item_value"}

    # Act
    result = get_object_id(**parameter)

    # Assert
    assert result == "item_value"


def test_get_object_id_fail_key():
    """
    This test checks behavior when the key is missing and
    the function get_object_id() should raise a ResourceException.
    """
    # Arrange
    parameter = {"item": "item_value"}

    # Act
    with pytest.raises(ResourceException) as e:
        get_object_id(**parameter)

    # Assert
    assert e.value.detail == "Resource was not found"



def test_get_object_id_fail_value():
    """
    This test checks behavior when the value is missing and
    the function get_object_id() should raise a ResourceException.
    """
    # Arrange
    parameter = {"item_id": 0}

    # Act
    with pytest.raises(ResourceException) as e:
        get_object_id(**parameter)

    # Assert
    assert e.value.detail == "Resource was not found"


def test_get_object_success():
    """This test checks that get_object() returns an existing object."""
    # Arrange
    mock_model = MagicMock()
    mock_instance = MagicMock()
    mock_model.objects.get.return_value = mock_instance

    # Act
    result = get_object(mock_model, 1)

    # Assert
    assert result is mock_instance
    mock_model.objects.get.assert_called_once_with(pk=1)


def test_get_object_not_found():
    """
    This test checks behavior when the object does not exist.
    The function get_object() should raise a ResourceException.
    """
    # Arrange
    class FakeModel:
        __name__ = "page"
        DoesNotExist = ResourceException

        class objects:
            @staticmethod
            def get(pk):
                raise ResourceException("Resource is not found")

    # Act
    with pytest.raises(ResourceException) as e:
        get_object(FakeModel, 1)

    # Assert
    assert "Resource was not found" in str(e.value)