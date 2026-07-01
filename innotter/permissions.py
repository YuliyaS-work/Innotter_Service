"""
This file contains permission classes for pages, posts and tags.
Each permission checks user roles: ADMIN, MODERATOR or USER.
ADMIN can do all actions.
MODERATOR can work with objects in their group.
USER can work only with their own objects.
Some actions are open for all authenticated users.
"""
from rest_framework.permissions import BasePermission

def check_access(
        request,
        obj,
        allow_admin=False,
        allow_moderator=False,
        allow_user=False
):
    """
    Check access rules for the object.

    ADMIN can always do it.
    MODERATOR can do it if group ID matches.
    USER can do it if he is the owner (user ID matches).
    """
    roles = request.auth_user["roles"]
    user_id = request.auth_user["user_id"]
    group_id = request.auth_user["group_id"]

    if "ADMIN" in roles and allow_admin:
        return True

    if "MODERATOR" in roles and allow_moderator:
        return group_id == getattr(obj, "group_id", None)

    if "USER" in roles and allow_user:
        return user_id == getattr(obj, "user_id", None)

    return False


class AllowAllAuthenticatedUser(BasePermission):
    """Allow action for all roles without filter."""
    def has_permission(self, request, view):
        return True


class AllowAllRoles(BasePermission):
    """Allow admin, moderator of the same group or page owner to work with object."""
    def has_object_permission(self, request, view, obj):
        return check_access(request, obj, allow_admin=True, allow_moderator=True, allow_user=True)


class IsUserOwner(BasePermission):
    """Allow only the page owner to work with an object."""
    def has_object_permission(self, request, view, obj):
        return check_access(request, obj, allow_user=True)


class IsAdminModerator(BasePermission):
    """Allow admin or moderator of the same group to work with object."""
    def has_object_permission(self, request, view, obj):
        return check_access(request,obj, allow_admin=True, allow_moderator=True)