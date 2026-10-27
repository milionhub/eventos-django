from unittest.mock import patch

import pytest
from django.db.utils import OperationalError
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_reports_api_and_database_ok(api_client):
    response = api_client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"api": True, "database": True}


def test_health_returns_503_when_database_is_down(api_client):
    with patch("apps.core.views.connection.cursor", side_effect=OperationalError):
        response = api_client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json() == {"api": True, "database": False}
