from django.urls import path

from innotter.views import FeedListAPIView


urlpatterns = [
    path("api/feed/", FeedListAPIView.as_view())
]