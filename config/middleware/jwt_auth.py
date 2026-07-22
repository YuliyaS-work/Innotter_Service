"""
JWT authentication middleware for Django.

This middleware extracts the access token from cookies, validates it through the
User Management Service for all incoming requests before they reach Django or DRF views.
"""
import logging

import httpx
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class JwtAuthMiddleware:
    """
    Middleware that performs JWT authentication for incoming requests.

    Responsibilities:
    - Get access_token from cookie.
    - Validate the token via User Management Service (/auth/validate-token).
    - Provided decoded user data with request.auth_user.
    - Return JSON error responses for
         missing token (401),
         invalid token (401),
         User Management Service connection issues (503).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.COOKIES.get("access_token")
        logger.info(f"[JwtAuthMiddleware] Token received, token={token}")

        if not token:
            logger.info("[JwtAuthMiddleware] Missing token")
            return JsonResponse(
                {"detail": "The user is not authenticated", "status_code": 401},
                status=401
            )

        try:
            with httpx.Client(timeout=5) as client:
                response_auth = client.get(
                    "http://ums_app:8000/auth/validate-token",
                    headers={"Authorization": f"Bearer {token}"}
                )

        except httpx.RequestError:
            logger.error("[JwtAuthMiddleware] Error while building request")
            return JsonResponse(
                {"detail": "User manage service is unavailable", "status_code": 503},
                status=503
            )


        if response_auth.status_code != 200:
            logger.warning("[JwtAuthMiddleware] Invalid token")
            return JsonResponse(
                {"detail": "Invalid token", "status_code": 401},
                status=401
            )

        request.auth_user = response_auth.json()

        logger.info("[JwtAuthMiddleware] Token validated successfully")

        return self.get_response(request)