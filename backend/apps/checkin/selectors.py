from datetime import datetime

from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.checkin.models import CheckInLog
from apps.events.models import Event
from apps.organizations.models import Membership
from apps.ticketing.models import Reservation, Ticket


def validatable_events(user: User, now: datetime) -> QuerySet[Event]:
    """Published events not over yet where `user` may validate (RN-28), soonest first."""
    organizer_of = Membership.objects.filter(
        user=user, role__in=[Membership.Role.OWNER, Membership.Role.MANAGER]
    ).values("organization_id")
    return (
        Event.objects.filter(status=Event.Status.PUBLISHED, end_at__gt=now)
        .filter(Q(organization_id__in=organizer_of) | Q(staff__user=user))
        .select_related("organization")
        .distinct()
        .order_by("start_at")
    )


def event_in_my_organizations(user: User, event_id: int) -> Event | None:
    """An event of an organization the user belongs to. Any other is a 404 (RN-06)."""
    return (
        Event.objects.filter(pk=event_id, organization__memberships__user=user)
        .select_related("organization")
        .first()
    )


def checkin_stats(event: Event) -> dict[str, int]:
    """How many people are in, out of those with a confirmed reservation."""
    return {
        "validated": Ticket.objects.filter(
            reservation__event=event, status=Ticket.Status.USED
        ).count(),
        "expected": Reservation.objects.filter(
            event=event, status=Reservation.Status.CONFIRMED
        ).count(),
    }


def recent_logs(event: Event, limit: int = 20) -> QuerySet[CheckInLog]:
    return (
        CheckInLog.objects.filter(event=event)
        .select_related("ticket__reservation__user", "ticket__reservation__ticket_type")
        .order_by("-checked_at", "-pk")[:limit]
    )
