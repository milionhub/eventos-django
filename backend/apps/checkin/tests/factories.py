from datetime import timedelta

from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event, EventStaff, TicketType
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory
from apps.ticketing.models import Ticket
from apps.ticketing.services import reserve


def open_event(**kwargs) -> Event:
    """A published event starting in one hour: its door (3 h before) is already open."""
    start = kwargs.pop("start_at", timezone.now() + timedelta(hours=1))
    kwargs.setdefault("end_at", start + timedelta(hours=3))
    kwargs.setdefault("status", Event.Status.PUBLISHED)
    return EventFactory(start_at=start, **kwargs)


def ticket_for(event: Event, **user_kwargs) -> Ticket:
    """A confirmed reservation's ticket, booked before the event (bypassing RN-18 timing)."""
    ticket_type = TicketType.objects.filter(event=event, name="General").first() or (
        TicketTypeFactory(event=event, name="General", capacity=100)
    )
    user = UserFactory(**user_kwargs)
    start_at = event.start_at
    if start_at <= timezone.now():  # reserve() only books events that have not started
        Event.objects.filter(pk=event.pk).update(start_at=timezone.now() + timedelta(hours=1))
    ticket = reserve(user=user, ticket_type_id=ticket_type.pk).ticket
    Event.objects.filter(pk=event.pk).update(start_at=start_at)
    event.refresh_from_db()
    return ticket


def staff_of(event: Event):
    """A STAFF member assigned to the event (RN-28)."""
    user = MembershipFactory(organization=event.organization, role=Membership.Role.STAFF).user
    EventStaff.objects.create(event=event, user=user)
    return user
