from django.db.models import QuerySet

from apps.events.models import Event
from apps.organizations.models import Organization


def events_of(organization: Organization, *, status: str | None = None) -> QuerySet[Event]:
    """An organization's events for its organizers, soonest first."""
    events = Event.objects.filter(organization=organization)
    if status:
        events = events.filter(status=status)
    return events.order_by("start_at")


def event_of(organization: Organization, event_id: int) -> Event | None:
    """Scoped by organization: another organization's event id finds nothing (→ 404)."""
    return (
        Event.objects.filter(organization=organization, pk=event_id)
        .prefetch_related("ticket_types")
        .first()
    )
