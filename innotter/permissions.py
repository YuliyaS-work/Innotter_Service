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


class AllowAllRoles(BasePermission):
    """Allow action for all roles without filter."""
    def has_permission(self, request, view):
        return True


class CreatePage(AllowAllRoles):
    """Allow all roles to create a page."""
    pass


class GetPages(AllowAllRoles):
    """Allow all roles to get pages."""
    pass


class FollowUnfollowPage(AllowAllRoles):
    """Allow all roles to follow or unfollow a page."""
    pass


class DeletePage(BasePermission):
    """Allow admin, moderator of the same group or page owner to delete the page."""
    def has_object_permission(self, request, view, page):
        return check_access(request, page, allow_admin=True, allow_moderator=True, allow_user=True)


class UpdatePage(BasePermission):
    """Allow only the page owner to update the page."""
    def has_object_permission(self, request, view, page):
        return check_access(request, page, allow_user=True)


class GetFollowers(BasePermission):
    """Allow admin, moderator of the same group or page owner to view followers."""
    def has_object_permission(self, request, view, page):
        return check_access(request, page, allow_admin=True, allow_moderator=True, allow_user=True)


class BlockPage(BasePermission):
    """Allow admin or moderator of the same group to block the page."""
    def has_object_permission(self, request, view, page):
        return check_access(request, page, allow_admin=True, allow_moderator=True)


class CreatePost(BasePermission):
    """Allow only the page owner to create a post."""
    def has_object_permission(self, request, view, page):
        return check_access(request, page, allow_user=True)


class UpdatePost(BasePermission):
    """Allow admin, moderator of the same group or page owner to update the post."""
    def has_object_permission(self, request, view, post):
        return check_access(request, post.page, allow_admin=True, allow_moderator=True, allow_user=True)


class DeletePost(BasePermission):
    """Allow admin, moderator of the same group or page owner to delete the post."""
    def has_object_permission(self, request, view, post):
        return check_access(request, post.page, allow_admin=True, allow_moderator=True, allow_user=True)


class CreateTag(AllowAllRoles):
    """Allow all roles to create a tag."""
    pass


class GetTags(AllowAllRoles):
    """Allow all roles to view tags."""
    pass