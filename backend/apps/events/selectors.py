from datetime import date, datetime, time

from django.db.models import F, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Event, EventStaff, TicketType
from apps.organizations.models import Organization

Status = Event.Status

# --- Organizer side -----------------------------------------------------------------------
# `staff_user` narrows everything to the events that STAFF member is assigned to (§4).


def events_of(
    organization: Organization, *, status: str | None = None, staff_user: User | None = None
) -> QuerySet[Event]:
    """An organization's events for its organizers, soonest first."""
    events = Event.objects.filter(organization=organization)
    if staff_user is not None:
        events = events.filter(staff__user=staff_user)
    if status:
        events = events.filter(status=status)
    return events.order_by("start_at")


def event_of(
    organization: Organization, event_id: int, *, staff_user: User | None = None
) -> Event | None:
    """Scoped by organization: another organization's event id finds nothing (→ 404)."""
    return (
        events_of(organization, staff_user=staff_user)
        .filter(pk=event_id)
        .prefetch_related("ticket_types")
        .first()
    )


def ticket_types_of(event: Event) -> QuerySet[TicketType]:
    return TicketType.objects.filter(event=event)


def staff_of(event: Event) -> QuerySet[EventStaff]:
    return EventStaff.objects.filter(event=event).select_related("user")


# --- Public side ----------------------------------------------------------------------------


def _with_availability(events: QuerySet[Event]) -> QuerySet[Event]:
    seats_left = Sum(F("ticket_types__capacity") - F("ticket_types__reserved_count"))
    return events.annotate(available=Coalesce(seats_left, 0))


def public_events(
    *, q: str = "", from_date: date | None = None, now: datetime | None = None
) -> QuerySet[Event]:
    """Published events that have not finished (RN-08), soonest first."""
    now = now or timezone.now()
    events = Event.objects.filter(status=Status.PUBLISHED, end_at__gt=now)
    if q:
        events = events.filter(Q(title__icontains=q) | Q(location__icontains=q))
    if from_date:
        start_of_day = timezone.make_aware(datetime.combine(from_date, time.min))
        events = events.filter(start_at__gte=start_of_day)
    return _with_availability(events.select_related("organization")).order_by("start_at")


def public_event(slug: str) -> Event | None:
    """A published event by slug, finished ones included so old links still explain it."""
    return (
        Event.objects.filter(slug=slug, status=Status.PUBLISHED)
        .select_related("organization")
        .prefetch_related("ticket_types")
        .first()
    )
