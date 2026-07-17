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
    """ Exception class for error when the object is not found."""
    status_code = 404
    detail: str = "Resource is not found"


class LogicException(BaseAPIException):
    """Raised when a user action violates a business logic."""
    status_code = 400
    detail: str = "This action is not allowed"


class S3StorageError(BaseAPIException):
    """
    Raised when errors exist while working with s3 storage.
    """
    detail: str = "Error while working with s3 storage."