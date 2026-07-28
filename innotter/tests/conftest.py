import pytest

from rest_framework.test import APIRequestFactory

@pytest.fixture
def auth_user():
    return {
        "user_id": 123,
        "group_id": 1,
        "roles": ["USER"]
    }

@pytest.fixture
def page_data():
    return {
        "id": 1,
        "name": "fake page",
        "description": "description",
        "tags": [1]
    }


@pytest.fixture
def post_data():
    return {
        "id": 1,
        "page": 1,
        "content": "test",
        "reply_to": 4,
        "likes_count": 0,
        "is_liked": False
    }


@pytest.fixture
def api_factory():
    return APIRequestFactory()