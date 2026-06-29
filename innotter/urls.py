from django.urls import path

from innotter.views import FeedAPIView


urlpatterns = [
    path("api/feed/", FeedAPIView.as_view())
]