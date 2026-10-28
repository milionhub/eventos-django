import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.ticketing.tests.factories import bookable_ticket_type

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_book_a_seat():
    ticket_type = bookable_ticket_type(name="General")

    response = client_for(UserFactory()).post(
        reverse("reservations"), {"ticket_type": ticket_type.pk}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "CONFIRMED"
    assert body["ticket_type"]["name"] == "General"
    assert body["event"]["slug"] == ticket_type.event.slug
    assert body["ticket"]["status"] == "VALID"
    assert "token" not in body["ticket"]  # only in the ticket detail and its QR


def test_booking_requires_an_account():
    response = APIClient().post(reverse("reservations"), {"ticket_type": bookable_ticket_type().pk})

    assert response.status_code == 401


def test_business_errors_are_explained():
    ticket_type = bookable_ticket_type(capacity=1)
    user = UserFactory()
    client_for(user).post(reverse("reservations"), {"ticket_type": ticket_type.pk})

    again = client_for(user).post(reverse("reservations"), {"ticket_type": ticket_type.pk})
    full = client_for(UserFactory()).post(reverse("reservations"), {"ticket_type": ticket_type.pk})
    missing = client_for(user).post(reverse("reservations"), {"ticket_type": 999_999})

    assert (again.status_code, again.json()["code"]) == (409, "already_reserved")
    assert (full.status_code, full.json()["code"]) == (409, "sold_out")
    assert (missing.status_code, missing.json()["code"]) == (404, "ticket_type_not_found")


def test_booking_is_throttled():
    client = client_for(UserFactory())

    statuses = [
        client.post(reverse("reservations"), {"ticket_type": 999_999}).status_code
        for _ in range(21)
    ]

    assert statuses[:20] == [404] * 20
    assert statuses[20] == 429
