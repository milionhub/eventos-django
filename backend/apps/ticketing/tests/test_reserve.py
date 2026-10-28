from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.ticketing.models import Reservation, Ticket
from apps.ticketing.services import (
    AlreadyReserved,
    EventNotBookable,
    SoldOut,
    TicketTypeNotFound,
    reserve,
)
from apps.ticketing.tests.factories import assert_counters_match_reservations, bookable_ticket_type

pytestmark = pytest.mark.django_db


def test_reserve_takes_a_seat_and_issues_a_ticket():
    ticket_type, user = bookable_ticket_type(capacity=10), UserFactory()

    reservation = reserve(user=user, ticket_type_id=ticket_type.pk)

    ticket_type.refresh_from_db()
    assert ticket_type.reserved_count == 1
    assert reservation.status == Reservation.Status.CONFIRMED
    assert reservation.event == ticket_type.event
    assert reservation.ticket.status == Ticket.Status.VALID
    assert len(reservation.ticket.token) >= 40  # secrets.token_urlsafe(32)
    assert_counters_match_reservations()


def test_tokens_are_unique_and_unguessable():
    ticket_type = bookable_ticket_type(capacity=5)

    tokens = {
        reserve(user=UserFactory(), ticket_type_id=ticket_type.pk).ticket.token for _ in "abc"
    }

    assert len(tokens) == 3


def test_sold_out():
    ticket_type = bookable_ticket_type(capacity=1)
    reserve(user=UserFactory(), ticket_type_id=ticket_type.pk)

    with pytest.raises(SoldOut):
        reserve(user=UserFactory(), ticket_type_id=ticket_type.pk)
    assert_counters_match_reservations()


def test_one_reservation_per_user_and_event_even_across_categories():
    general = bookable_ticket_type(capacity=10)
    vip = TicketTypeFactory(event=general.event, capacity=10)
    user = UserFactory()
    reserve(user=user, ticket_type_id=general.pk)

    with pytest.raises(AlreadyReserved):
        reserve(user=user, ticket_type_id=vip.pk)
    assert_counters_match_reservations()


def test_the_same_user_can_book_different_events():
    user = UserFactory()

    reserve(user=user, ticket_type_id=bookable_ticket_type().pk)
    reserve(user=user, ticket_type_id=bookable_ticket_type().pk)

    assert Reservation.objects.filter(user=user).count() == 2


@pytest.mark.parametrize("status", [Event.Status.DRAFT, Event.Status.CANCELLED])
def test_unpublished_events_are_not_bookable(status):
    ticket_type = TicketTypeFactory(event=EventFactory(status=status))

    with pytest.raises(TicketTypeNotFound):
        reserve(user=UserFactory(), ticket_type_id=ticket_type.pk)


def test_unknown_category():
    with pytest.raises(TicketTypeNotFound):
        reserve(user=UserFactory(), ticket_type_id=999_999)


def test_events_that_already_started_are_not_bookable():
    started = timezone.now() - timedelta(minutes=5)
    event = EventFactory(
        status=Event.Status.PUBLISHED, start_at=started, end_at=started + timedelta(hours=2)
    )
    ticket_type = TicketTypeFactory(event=event)

    with pytest.raises(EventNotBookable):
        reserve(user=UserFactory(), ticket_type_id=ticket_type.pk)
    ticket_type.refresh_from_db()
    assert ticket_type.reserved_count == 0


def test_the_database_rejects_a_second_confirmed_reservation():
    """The partial unique index, without the service: the last line of defence (RN-17)."""
    reservation = reserve(user=UserFactory(), ticket_type_id=bookable_ticket_type().pk)

    with pytest.raises(IntegrityError), transaction.atomic():
        Reservation.objects.create(
            user=reservation.user, event=reservation.event, ticket_type=reservation.ticket_type
        )


def test_a_cancelled_reservation_does_not_block_booking_again():
    """The unique index is partial: only CONFIRMED rows count (prepares RN-24)."""
    reservation = reserve(user=UserFactory(), ticket_type_id=bookable_ticket_type().pk)
    Reservation.objects.filter(pk=reservation.pk).update(status=Reservation.Status.CANCELLED)

    Reservation.objects.create(
        user=reservation.user, event=reservation.event, ticket_type=reservation.ticket_type
    )
