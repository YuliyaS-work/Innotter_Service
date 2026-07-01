from django.urls import path

from innotter.views import FeedAPIView, PageCreateAPIView, PageDeleteAPIView, PagePostsGetAPIView

urlpatterns = [
    path("api/feed/", FeedAPIView.as_view(), name="user_feed"),
    path("api/page/", PageCreateAPIView.as_view(), name="new_page"),
    path("api/page/<int:page_id>", PageDeleteAPIView.as_view(), name="delete_page"),
    path("api/page/<int:page_id>/posts", PagePostsGetAPIView.as_view(), name="post_list"),
]