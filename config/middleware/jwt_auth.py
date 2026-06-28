import httpx
from django.http import JsonResponse


class JwtAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.COOKIES.get("access_token")
        print(token)

        if not token:
            return JsonResponse({"detail": "The user is not authenticated"}, status=401)

        try:
            with httpx.Client(timeout=5) as client:
                response_auth = client.get(
                    "http://ums_app:8000/auth/validate-token",
                    headers={"Authorization": f"Bearer {token}"}
                )

        except httpx.RequestError:
            return JsonResponse({"detail": f"User manage service is unavailable"}, status=503)

        if response_auth.status_code != 200:
            return JsonResponse({"detail": "Invalid token"}, status=401)

        request.auth_user = response_auth.json()

        return self.get_response(request)