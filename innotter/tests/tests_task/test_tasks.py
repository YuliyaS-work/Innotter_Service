from unittest.mock import patch, MagicMock

from innotter.tasks import unblock_pages, delete_user_data


@patch("innotter.tasks.logger")
@patch("innotter.tasks.Page.objects.filter")
def test_ublock_pages_success(
        mock_page_filter,
        mock_logger
):
    """
    This test checks that unblock_page() unblocks a page
    when its is_blocked status is True.
    """
    # Arrange
    page_1 = MagicMock()
    page_2 = MagicMock()
    mock_page_filter.return_value = [page_1, page_2]

    # Act
    unblock_pages()

    # Assert
    assert page_1.is_blocked is False
    assert page_1.unblock_date is None
    assert page_2.is_blocked is False
    assert page_2.unblock_date is None

    page_1.save.assert_called_once_with(update_fields=["is_blocked", "unblock_date"])
    page_2.save.assert_called_once_with(update_fields=["is_blocked", "unblock_date"])

    assert mock_logger.info.call_count == 2


@patch("innotter.tasks.Page.save")
@patch("innotter.tasks.Page.objects.filter")
def test_ublock_pages_fail(
        mock_page_filter,
        mock_save,
        caplog
):
    """
    This test checks that unblock_pages() writes an error log
    when a page cannot be unblocked.
    """
    # Arrange
    page_1 = MagicMock()
    page_2 = MagicMock()
    mock_page_filter.return_value = [page_1, page_2]

    page_1.save.side_effect = Exception()
    page_2.save.side_effect = Exception()

    caplog.set_level("ERROR")

    # Act
    unblock_pages()

    # Assert
    assert "Failed to unblock page" in caplog.text


@patch("innotter.tasks.Post.objects.filter")
@patch("innotter.tasks.Followers.objects.filter")
@patch("innotter.tasks.Likes.objects.filter")
@patch("innotter.tasks.Page.objects.filter")
def test_delete_user_data_success(
        mock_page_filter,
        mock_likes_filter,
        mock_followers_filter,
        mock_post_likes_filter,
        caplog
):
    """
    This test checks that delete_user_data() removes all related user data correctly.
    """
    # Arrange
    user_id = "123"
    page = MagicMock()
    mock_page_filter.return_value.iterator.return_value = [page]

    like = MagicMock()
    like.post_id = 1
    mock_likes_filter.return_value.iterator.return_value = [like]

    follower = MagicMock()
    follower.page_id = 1
    mock_followers_filter.return_value.iterator.return_value = [follower]

    mock_post_likes_filter.return_value.update.return_value = None
    mock_page_filter.return_value.update.return_value = None

    caplog.set_level("INFO")

    # Act
    delete_user_data(user_id)

    # Assert
    assert "User data were deleted successfully" in caplog.text
    page.delete.assert_called_once()
    like.delete.assert_called_once()
    follower.delete.assert_called_once()