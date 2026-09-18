from unittest.mock import MagicMock, patch

from innotter.views import FeedAPIView


class TestFeedAPIView:
    """
    Tests for FeedAPIView.
    Tests check the GET method behavior.
    They verify correct filtering, serialization, and response data.
    """

    def setup_method(self):
        self.view = FeedAPIView.as_view()

    @patch("innotter.views.Followers.objects.filter")
    @patch("innotter.views.Post.objects.filter")
    @patch.object(FeedAPIView, "serializer_class")
    def test_get_success(
            self,
            mock_serializer_class,
            mock_post_filter,
            mock_followers_filter,
            auth_user,
            post_data,
            api_factory
    ):
        """
        This test checks GET method when posts exist.
        The view should return status 200 and serialized data.
        It also checks that filters and serializer are called correctly.
        """
        # Arrange
        request = api_factory.get("/feed/")
        request.auth_user = auth_user


        followers_queryset = MagicMock()
        followers_queryset.values_list.return_value = [10, 20]
        mock_followers_filter.return_value = followers_queryset

        post_queryset = MagicMock()

        post_queryset.select_related.return_value = post_queryset
        post_queryset.prefetch_related.return_value = post_queryset
        post_queryset.order_by.return_value = post_queryset
        mock_post_filter.return_value = post_queryset

        serializer = MagicMock()
        serializer.data = [post_data]
        mock_serializer_class.return_value = serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == serializer.data

        mock_followers_filter.assert_called_once_with(
            user_id=123
        )

        mock_post_filter.assert_called_once_with(
            page_id__in=[10, 20],
            page__is_blocked=False,
        )

        post_queryset.select_related.assert_called_once_with("page")
        post_queryset.prefetch_related.assert_called_once_with("page__tags")
        post_queryset.order_by.assert_called_once_with("-created_at")

        mock_serializer_class.assert_called_once_with(post_queryset, many=True)


    @patch("innotter.views.Followers.objects.filter")
    @patch("innotter.views.Post.objects.filter")
    @patch.object(FeedAPIView, "serializer_class")
    def test_get_without_followers(
            self,
            mock_serializer_class,
            mock_post_filter,
            mock_followers_filter,
            auth_user,
            api_factory
    ):
        """
        This test checks GET method when no posts are returned.
        The view should return status 200.
        The serializer should return an empty list.
        """
        # Arrange
        request = api_factory.get("/feed/")
        request.auth_user = auth_user


        followers_queryset = MagicMock()
        followers_queryset.values_list.return_value = [10, 20]
        mock_followers_filter.return_value = followers_queryset

        post_queryset = MagicMock()

        post_queryset.select_related.return_value = post_queryset
        post_queryset.prefetch_related.return_value = post_queryset
        post_queryset.order_by.return_value = post_queryset
        mock_post_filter.return_value = post_queryset

        serializer = MagicMock()
        serializer.data = []
        mock_serializer_class.return_value = serializer

        # Act
        response = self.view(request)

        # Assert
        assert response.status_code == 200
        assert response.data == serializer.data

        mock_followers_filter.assert_called_once_with(
            user_id=123
        )

        mock_post_filter.assert_called_once_with(
            page_id__in=[10, 20],
            page__is_blocked=False,
        )

        post_queryset.select_related.assert_called_once_with("page")
        post_queryset.prefetch_related.assert_called_once_with("page__tags")
        post_queryset.order_by.assert_called_once_with("-created_at")

        mock_serializer_class.assert_called_once_with(post_queryset, many=True)