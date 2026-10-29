from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event
from apps.events.services import (
    CapacityBelowAllocated,
    EventNotEditable,
    EventNotPublishable,
    InvalidDates,
    InvalidTransition,
    PastDatesNotAllowed,
    cancel_event,
    create_event,
    publish_blockers,
    publish_event,
    update_event,
)
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.organizations.tests.factories import OrganizationFactory

pytestmark = pytest.mark.django_db
Status = Event.Status


def in_days(days: float):
    return timezone.now() + timedelta(days=days)


def publishable_event(**kwargs) -> Event:
    event = EventFactory(**kwargs)
    TicketTypeFactory(event=event)
    return event


def published_event(**kwargs) -> Event:
    return publish_event(event=publishable_event(**kwargs))


# --- create -----------------------------------------------------------------------


def test_new_events_are_drafts_with_a_unique_slug():
    organization, user = OrganizationFactory(), UserFactory()
    data = {
        "organization": organization,
        "user": user,
        "title": "Jazz en Apolo",
        "location": "Barcelona",
        "start_at": in_days(7),
        "end_at": in_days(7.1),
        "capacity": 200,
    }

    first, second = create_event(**data), create_event(**data)

    assert first.status == Status.DRAFT
    assert first.created_by == user
    assert (first.slug, second.slug) == ("jazz-en-apolo", "jazz-en-apolo-2")


def test_create_rejects_an_end_before_the_start():
    with pytest.raises(InvalidDates):
        create_event(
            organization=OrganizationFactory(),
            user=UserFactory(),
            title="Al revés",
            location="Barcelona",
            start_at=in_days(7),
            end_at=in_days(6),
            capacity=10,
        )


# --- publish (RN-09) ----------------------------------------------------------------


def test_publish_a_ready_draft():
    event = publish_event(event=publishable_event())

    assert event.status == Status.PUBLISHED
    assert event.published_at is not None


def test_publish_blockers_explain_what_is_missing():
    event = EventFactory(start_at=in_days(-1), end_at=in_days(1))  # started and no categories

    assert publish_blockers(event) == [
        "La fecha de inicio debe ser futura.",
        "Añade al menos una categoría de entrada.",
    ]


def test_publish_blockers_catch_an_end_before_the_start():
    """The database refuses to store it (CHECK event_ends_after_start): checked in memory."""
    event = TicketTypeFactory(event=EventFactory(start_at=in_days(2))).event
    event.end_at = in_days(1)

    assert publish_blockers(event) == ["La fecha de fin debe ser posterior a la de inicio."]


def test_update_rejects_fields_that_are_not_editable():
    """A programming error, not user input: the serializer never sends these."""
    with pytest.raises(ValueError, match="slug"):
        update_event(event=EventFactory(), slug="otro")


def test_cannot_publish_without_ticket_types():
    with pytest.raises(EventNotPublishable, match="categoría de entrada"):
        publish_event(event=EventFactory())


def test_cannot_publish_twice():
    event = published_event()

    with pytest.raises(InvalidTransition):
        publish_event(event=event)


# --- cancel (RN-07) -----------------------------------------------------------------


@pytest.mark.parametrize("make", [EventFactory, published_event])
def test_drafts_and_published_events_can_be_cancelled(make):
    event = cancel_event(event=make())

    assert event.status == Status.CANCELLED
    assert event.cancelled_at is not None


def test_cancelled_is_final():
    event = cancel_event(event=publishable_event())

    with pytest.raises(InvalidTransition):
        cancel_event(event=event)
    with pytest.raises(InvalidTransition):
        publish_event(event=event)  # no way back to draft or published


def test_a_finished_event_cannot_be_cancelled():
    event = published_event()
    Event.objects.filter(pk=event.pk).update(start_at=in_days(-2), end_at=in_days(-1))

    with pytest.raises(InvalidTransition):
        cancel_event(event=event)


# --- edit (RN-11, RN-13) ------------------------------------------------------------


def test_drafts_can_change_anything_even_past_dates():
    event = EventFactory(start_at=in_days(-3), end_at=in_days(-2))

    event = update_event(event=event, title="Nuevo título", start_at=in_days(-1), end_at=in_days(1))

    assert event.title == "Nuevo título"
    assert event.slug.startswith("concierto-")  # the slug never changes


def test_published_events_can_move_to_future_dates():
    event = published_event()

    event = update_event(event=event, start_at=in_days(10), end_at=in_days(10.1))

    assert event.start_at > timezone.now()


def test_published_events_cannot_move_to_past_dates():
    with pytest.raises(PastDatesNotAllowed):
        update_event(event=published_event(), start_at=in_days(-1), end_at=in_days(1))


def test_edit_keeps_end_after_start():
    with pytest.raises(InvalidDates):
        update_event(event=EventFactory(), end_at=in_days(1))  # starts in 7 days


def test_cancelled_events_cannot_be_edited():
    event = cancel_event(event=EventFactory())

    with pytest.raises(EventNotEditable):
        update_event(event=event, title="Otro")


def test_finished_events_cannot_be_edited():
    event = published_event()
    Event.objects.filter(pk=event.pk).update(start_at=in_days(-2), end_at=in_days(-1))

    with pytest.raises(EventNotEditable):
        update_event(event=event, title="Otro")


def test_capacity_cannot_drop_below_what_categories_hold():
    event = EventFactory(capacity=100)
    TicketTypeFactory(event=event, capacity=60)
    TicketTypeFactory(event=event, capacity=30)

    update_event(event=event, capacity=90)  # exactly what is allocated: fine
    with pytest.raises(CapacityBelowAllocated):
        update_event(event=event, capacity=89)
