"""Database constraints: the last line of defence even if a service has a bug."""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.events.models import Event
from apps.events.tests.factories import EventFactory, TicketTypeFactory

pytestmark = pytest.mark.django_db


def test_event_must_end_after_it_starts():
    start = timezone.now() + timedelta(days=1)

    with pytest.raises(IntegrityError):
        EventFactory(start_at=start, end_at=start)


def test_event_capacity_must_be_positive():
    with pytest.raises(IntegrityError):
        EventFactory(capacity=0)


def test_ticket_type_cannot_be_oversold():
    with pytest.raises(IntegrityError):
        TicketTypeFactory(capacity=10, reserved_count=11)


def test_ticket_type_names_are_unique_per_event():
    ticket_type = TicketTypeFactory(name="VIP")

    with pytest.raises(IntegrityError):
        TicketTypeFactory(event=ticket_type.event, name="VIP")


@pytest.mark.parametrize(
    ("status", "ended", "finished"),
    [
        (Event.Status.PUBLISHED, True, True),
        (Event.Status.PUBLISHED, False, False),
        (Event.Status.DRAFT, True, False),  # only published events "finish" (RN-08)
        (Event.Status.CANCELLED, True, False),
    ],
)
def test_is_finished_is_computed(status, ended, finished):
    start = timezone.now() + timedelta(days=-2 if ended else 2)
    event = EventFactory(status=status, start_at=start, end_at=start + timedelta(hours=2))

    assert event.is_finished is finished
