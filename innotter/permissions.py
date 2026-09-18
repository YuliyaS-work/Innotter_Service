"""
This file contains permission classes for pages, posts and tags.
Each permission checks user roles: ADMIN, MODERATOR or USER.
ADMIN can do all actions.
MODERATOR can work with objects in their group.
USER can work only with their own objects.
Some actions are open for all authenticated users.
"""
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


def check_access(
        request: Request,
        obj: Any,
        allow_admin: bool = False,
        allow_moderator: bool = False,
        allow_user: bool = False
) -> bool:
    """
    Check access rules for the object.

    ADMIN can always do it.
    MODERATOR can do it if group ID matches.
    USER can do it if he is the owner (user ID matches).
    """
    roles: list[str] = request.auth_user["roles"]
    user_id: int = request.auth_user["user_id"]
    group_id: int | None = request.auth_user["group_id"]

    if "ADMIN" in roles and allow_admin:
        return True

    if "MODERATOR" in roles and allow_moderator:
        return group_id == getattr(obj, "group_id", None)

    if "USER" in roles and allow_user:
        owner_id = getattr(obj, "user_id", None)

        if owner_id is None:
            if hasattr(obj, "page"):
                owner_id = getattr(obj.page, "user_id", None)
        return user_id == owner_id
    return False


class AllowAllAuthenticatedUser(BasePermission):
    """Allow action for all roles without filter."""
    def has_permission(self, request: Request, view: APIView) -> bool:
        return True


class AllowAllRoles(BasePermission):
    """Allow admin, moderator of the same group or page owner to work with object."""
    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return check_access(request, obj, allow_admin=True, allow_moderator=True, allow_user=True)


class IsUserOwner(BasePermission):
    """Allow only the page owner to work with an object."""
    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return check_access(request, obj, allow_user=True)


class IsAdminModerator(BasePermission):
    """Allow admin or moderator of the same group to work with object."""
    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return check_access(request,obj, allow_admin=True, allow_moderator=True)


class ComplexApiPermission(BasePermission):
    """Combined permission class for different HTTP methods in a single endpoint."""
    method_permission: dict[str, type[BasePermission]] = {}

    def has_permission(self, request: Request, view: APIView) -> bool:
        return True

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        permission_class = self.method_permission.get(request.method)

        if permission_class is None:
            return False

        return permission_class().has_object_permission(request, view, obj)


class PageDetailPermission(ComplexApiPermission):
    """Combined permission class for PageDetailApiView endpoint"""
    method_permission: dict[str, type[BasePermission]] = {
        "GET": AllowAllRoles,
        "PATCH": IsUserOwner,
        "DELETE": IsUserOwner | IsAdminModerator
    }


class PostDetailPermission(ComplexApiPermission):
    """Combined permission class for PageDetailApiView endpoint"""
    method_permission: dict[str, type[BasePermission]] = {
        "PATCH": IsUserOwner | IsAdminModerator,
        "DELETE": IsUserOwner | IsAdminModerator
    }


class ImageDetailPermission(ComplexApiPermission):
    """Combined permission class for ImageDetailApiView endpoint"""
    method_permission: dict[str, type[BasePermission]] = {
        "GET": AllowAllAuthenticatedUser,
        "DELETE": IsUserOwner,
        "POST": IsUserOwner,
        "PUT": IsUserOwner
    }