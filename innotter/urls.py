"""
This file defines URL routes for the Innotter application.
It adds API endpoints for pages, posts and the user feed.
"""
from django.urls import path

from innotter.views import FeedAPIView, PageCreateAPIView, PageDetailAPIView, PageFollowAPIView, PageUnfollowAPIView, \
    PageFollowersGetAPIView, PageBlockAPIView, PostCreateAPIView

urlpatterns = [
    path("api/feed/", FeedAPIView.as_view(), name="user_feed"),
    path("api/page/", PageCreateAPIView.as_view(), name="new_page"),
    path("api/page/<int:page_id>/", PageDetailAPIView.as_view(), name="detail_page"),
    path("api/page/<int:page_id>/follow/", PageFollowAPIView.as_view(), name="follow_page"),
    path("api/page/<int:page_id>/unfollow/", PageUnfollowAPIView.as_view(), name="unfollow_page"),
    path("api/page/<int:page_id>/followers/", PageFollowersGetAPIView.as_view(), name="page_followers"),
    path("api/page/<int:page_id>/block/", PageBlockAPIView.as_view(), name="block_page"),
    path("api/page/<int:page_id>/post/", PostCreateAPIView.as_view(), name="new_post"),
]