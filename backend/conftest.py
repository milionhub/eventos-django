import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    # Throttling counters live in the cache: start every test with a clean slate.
    cache.clear()
