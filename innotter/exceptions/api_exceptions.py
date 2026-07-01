"""
Custom exception classes used for API error handling in Innotter Service.
"""
from rest_framework.exceptions import APIException


class BaseAPIException(APIException):
    """ Base class for custom API exceptions."""
    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail=None):
        if detail is not None:
            self.detail = detail
        super().__init__(detail=self.detail)

    def get_dict(self):
        return {
            "detail": self.detail,
            "status_code": self.status_code
        }

class ResourceException(BaseAPIException):
    status_code = 404
    detail = "Resource is not found"