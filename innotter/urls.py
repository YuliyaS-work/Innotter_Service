from django.urls import path

from innotter.views import FeedAPIView, PageCreateAPIView

urlpatterns = [
    path("api/feed/", FeedAPIView.as_view()),
    path("api/page/", PageCreateAPIView.as_view()),
]