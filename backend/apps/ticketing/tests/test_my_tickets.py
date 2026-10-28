from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.ticketing.models import Ticket
from apps.ticketing.qr import ticket_qr, ticket_qr_svg
from apps.ticketing.services import cancel_reservation, reserve
from apps.ticketing.tests.factories import bookable_ticket_type

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def booked_ticket(user=None, **event_kwargs) -> Ticket:
    if event_kwargs:
        event = EventFactory(status=Event.Status.PUBLISHED, **event_kwargs)
        ticket_type = TicketTypeFactory(event=event, name="General")
    else:
        ticket_type = bookable_ticket_type(name="General")
    return reserve(user=user or UserFactory(), ticket_type_id=ticket_type.pk).ticket


# --- list ---------------------------------------------------------------------------------


def test_my_tickets_lists_only_mine_without_tokens():
    me = UserFactory()
    mine = booked_ticket(me)
    booked_ticket()  # someone else's

    response = client_for(me).get(reverse("my-tickets"))

    assert response.status_code == 200
    data = response.json()
    assert [t["id"] for t in data] == [str(mine.pk)]
    assert data[0]["event"]["title"] == mine.reservation.event.title
    assert data[0]["event"]["image_url"] == ""  # no image uploaded for this event
    assert data[0]["ticket_type"]["name"] == "General"
    assert data[0]["reservation"]["status"] == "CONFIRMED"
    assert "token" not in data[0]


def test_cancelled_tickets_stay_in_the_list():
    me = UserFactory()
    ticket = booked_ticket(me)
    cancel_reservation(reservation=ticket.reservation, cancelled_by=me)

    data = client_for(me).get(reverse("my-tickets")).json()

    assert [(t["status"], t["reservation"]["status"]) for t in data] == [("CANCELLED", "CANCELLED")]


def test_my_tickets_requires_an_account():
    assert APIClient().get(reverse("my-tickets")).status_code == 401


# --- detail -------------------------------------------------------------------------------


def test_the_detail_carries_the_token_and_cancellation_info():
    ticket = booked_ticket()

    data = (
        client_for(ticket.reservation.user)
        .get(reverse("my-ticket", kwargs={"ticket_id": ticket.pk}))
        .json()
    )

    assert data["token"] == ticket.token
    assert data["can_cancel"] is True
    assert data["cancel_deadline"] is not None


def test_can_cancel_is_false_past_the_deadline():
    soon = timezone.now() + timedelta(hours=1)
    ticket = booked_ticket(start_at=soon, end_at=soon + timedelta(hours=2))

    data = (
        client_for(ticket.reservation.user)
        .get(reverse("my-ticket", kwargs={"ticket_id": ticket.pk}))
        .json()
    )

    assert data["can_cancel"] is False


# --- QR -----------------------------------------------------------------------------------


def test_the_qr_is_an_uncacheable_svg_of_the_token():
    ticket = booked_ticket()

    response = client_for(ticket.reservation.user).get(
        reverse("my-ticket-qr", kwargs={"ticket_id": ticket.pk}), HTTP_ACCEPT="image/svg+xml"
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert response["Cache-Control"] == "no-store"
    assert response.content.startswith(b"<svg")
    assert response.content == ticket_qr_svg(ticket.token)


def test_the_qr_holds_only_the_token_in_a_regular_qr_code():
    """RN-26, and a regular QR (not Micro QR) so any phone scanner can read it."""
    token = "x" * 43

    assert not ticket_qr(token).is_micro
    assert token.encode() not in ticket_qr_svg(token)  # encoded as modules, never as text


# --- isolation ----------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["my-ticket", "my-ticket-qr"])
def test_someone_elses_ticket_is_404(name):
    ticket = booked_ticket()

    response = client_for(UserFactory()).get(
        reverse(name, kwargs={"ticket_id": ticket.pk}), HTTP_ACCEPT="*/*"
    )

    assert response.status_code == 404
