"""
Custom DRF exception handler for Innotter Service.

Provides a unified JSON error format, handles BaseAPIException, extends DRF's
default exception handling, and logs unexpected errors.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response

from innotter.exceptions.api_exceptions import BaseAPIException

logger = logging.getLogger(__name__)

def global_exception_handler(exc, context):
    """
    Global DRF exception handler.

    Returns structured JSON for BaseAPIException.
    Uses DRF's default handler for standard framework errors.
    Returns a common 500 response for unexpected exceptions.
    """
    request = context.get("request")

    if isinstance(exc, BaseAPIException):
        logger.warning("[APIException]: status=%s | %s | path=%s", exc.status_code, exc.detail, request.path)
        return Response(exc.get_dict(), status=exc.status_code)

    response = exception_handler(exc, context)

    if response is not None:
        response.data['status_code'] = response.status_code
        return response

    logger.exception("Unhandled exception at %s | %s: %s",
                     request.path,
                     type(exc).__name__,
                     str(exc),
                     )

    return Response(
        {"detail": "Internal server error", "status_code": 500},
        status=500
    )