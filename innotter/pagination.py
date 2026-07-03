"""
This file defines the default pagination settings for API responses.
It uses PageNumberPagination to control page size and limit the maximum number of items.
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for API results."""
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 30