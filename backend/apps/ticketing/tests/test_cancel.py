from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event
from apps.events.services import TicketTypeInUse, cancel_event, delete_ticket_type
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.ticketing.models import Reservation, Ticket
from apps.ticketing.services import (
    AlreadyCancelled,
    CancellationWindowClosed,
    TicketAlreadyUsed,
    cancel_reservation,
    reserve,
)
from apps.ticketing.tests.factories import assert_counters_match_reservations, bookable_ticket_type

pytestmark = pytest.mark.django_db


def booked(**ticket_type_kwargs) -> Reservation:
    ticket_type = bookable_ticket_type(**ticket_type_kwargs)
    return reserve(user=UserFactory(), ticket_type_id=ticket_type.pk)


def hours_before_start(reservation: Reservation, hours: float):
    return reservation.event.start_at - timedelta(hours=hours)


# --- attendee (RN-20, RN-23, RN-24) ---------------------------------------------------------


def test_cancelling_frees_the_seat_and_cancels_the_ticket():
    reservation = booked(capacity=1)

    cancel_reservation(reservation=reservation, cancelled_by=reservation.user)

    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.CANCELLED
    assert reservation.cancelled_by == reservation.user
    assert reservation.cancelled_at is not None
    assert reservation.ticket.status == Ticket.Status.CANCELLED
    reserve(user=UserFactory(), ticket_type_id=reservation.ticket_type_id)  # the seat is free
    assert_counters_match_reservations()


def test_the_attendee_can_book_again_after_cancelling():
    reservation = booked()
    cancel_reservation(reservation=reservation, cancelled_by=reservation.user)

    again = reserve(user=reservation.user, ticket_type_id=reservation.ticket_type_id)

    assert again.status == Reservation.Status.CONFIRMED
    assert again.pk != reservation.pk  # a new reservation; the old one is not reactivated
    assert_counters_match_reservations()


def test_attendees_can_cancel_until_the_deadline():
    reservation = booked()

    cancel_reservation(
        reservation=reservation,
        cancelled_by=reservation.user,
        now=hours_before_start(reservation, 2),  # exactly at the deadline: still allowed
    )


def test_attendees_cannot_cancel_after_the_deadline():
    reservation = booked()

    with pytest.raises(CancellationWindowClosed, match="2 h"):
        cancel_reservation(
            reservation=reservation,
            cancelled_by=reservation.user,
            now=hours_before_start(reservation, 1.9),
        )


def test_cancelling_twice_is_rejected():
    reservation = booked()
    cancel_reservation(reservation=reservation, cancelled_by=reservation.user)

    with pytest.raises(AlreadyCancelled):
        cancel_reservation(reservation=reservation, cancelled_by=reservation.user)
    assert_counters_match_reservations()


def test_a_used_ticket_cannot_be_cancelled():
    reservation = booked()
    Ticket.objects.filter(reservation=reservation).update(status=Ticket.Status.USED)

    with pytest.raises(TicketAlreadyUsed):
        cancel_reservation(reservation=reservation, cancelled_by=reservation.user)


# --- organizer (RN-21) --------------------------------------------------------------------


def test_organizers_can_cancel_after_the_attendee_deadline():
    reservation, organizer = booked(), UserFactory()

    cancel_reservation(
        reservation=reservation,
        cancelled_by=organizer,
        as_organizer=True,
        now=hours_before_start(reservation, 0.5),
    )

    reservation.refresh_from_db()
    assert reservation.cancelled_by == organizer


def test_organizers_cannot_cancel_once_the_event_is_over():
    reservation = booked()

    with pytest.raises(CancellationWindowClosed):
        cancel_reservation(
            reservation=reservation,
            cancelled_by=UserFactory(),
            as_organizer=True,
            now=reservation.event.end_at + timedelta(minutes=1),
        )


# --- cancelling an event (RN-10) ---------------------------------------------------------


def test_cancelling_an_event_cancels_its_reservations_and_tickets():
    general = bookable_ticket_type(capacity=10)
    vip = TicketTypeFactory(event=general.event, capacity=5)
    reservations = [reserve(user=UserFactory(), ticket_type_id=t.pk) for t in (general, vip, vip)]
    organizer = UserFactory()

    cancel_event(event=general.event, by=organizer)

    for reservation in reservations:
        reservation.refresh_from_db()
        assert reservation.status == Reservation.Status.CANCELLED
        assert reservation.cancelled_by == organizer
        assert reservation.ticket.status == Ticket.Status.CANCELLED
    assert_counters_match_reservations()  # every counter back to 0


def test_cancelling_an_event_keeps_used_tickets_as_they_were():
    reservation = booked()
    Ticket.objects.filter(reservation=reservation).update(status=Ticket.Status.USED)

    cancel_event(event=reservation.event)

    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.CONFIRMED
    assert reservation.ticket.status == Ticket.Status.USED
    assert_counters_match_reservations()


# --- RN-15: categories with history --------------------------------------------------------


def test_a_category_with_only_cancelled_reservations_still_cannot_be_deleted():
    reservation = booked()
    TicketTypeFactory(event=reservation.event)  # so it is not the event's last category
    cancel_reservation(reservation=reservation, cancelled_by=reservation.user)

    with pytest.raises(TicketTypeInUse):
        delete_ticket_type(ticket_type=reservation.ticket_type)


# --- API ----------------------------------------------------------------------------------


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_cancel_my_reservation_over_http():
    reservation = booked()

    response = client_for(reservation.user).post(
        reverse("reservation-cancel", kwargs={"reservation_id": reservation.pk})
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["ticket"]["status"] == "CANCELLED"


def test_someone_elses_reservation_is_404():
    reservation = booked()

    response = client_for(UserFactory()).post(
        reverse("reservation-cancel", kwargs={"reservation_id": reservation.pk})
    )

    assert response.status_code == 404
    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.CONFIRMED


def test_late_cancellation_is_explained_over_http():
    soon = timezone.now() + timedelta(hours=1)
    event = EventFactory(
        status=Event.Status.PUBLISHED, start_at=soon, end_at=soon + timedelta(hours=2)
    )
    reservation = reserve(user=UserFactory(), ticket_type_id=TicketTypeFactory(event=event).pk)

    response = client_for(reservation.user).post(
        reverse("reservation-cancel", kwargs={"reservation_id": reservation.pk})
    )

    assert (response.status_code, response.json()["code"]) == (409, "cancellation_closed")
