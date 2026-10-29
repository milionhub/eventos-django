import pytest
from django.urls import reverse

from apps.checkin.tests.factories import open_event, ticket_for
from apps.core.middleware import API_CONTENT_SECURITY_POLICY

pytestmark = pytest.mark.django_db


def test_api_responses_carry_the_security_headers(api_client):
    response = api_client.get(reverse("health"))

    assert response["Content-Security-Policy"] == API_CONTENT_SECURITY_POLICY
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "same-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"


def test_the_ticket_svg_cannot_run_anything_when_opened_directly(api_client):
    ticket = ticket_for(open_event())
    api_client.force_authenticate(ticket.reservation.user)

    response = api_client.get(f"/api/v1/me/tickets/{ticket.pk}/qr.svg")

    assert response.status_code == 200
    assert response["Content-Security-Policy"] == API_CONTENT_SECURITY_POLICY


def test_the_swagger_docs_keep_their_scripts(api_client):
    response = api_client.get("/api/docs/")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response
