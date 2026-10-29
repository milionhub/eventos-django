from dataclasses import dataclass
from datetime import datetime

from django.db.models import Count, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from apps.accounts.models import User
from apps.checkin.models import CheckInLog
from apps.events.models import Event, TicketType
from apps.organizations.models import Membership, Organization
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


# --- Organizer stats (requirements.md R5) -----------------------------------------------------
# Every figure counts confirmed reservations only: `reserved_count` is kept by the services
# and released on every cancellation (ADR-0004).


@dataclass(frozen=True)
class EventStats:
    ticket_types: list[TicketType]  # annotated with `checked_in`
    cancelled: int
    scans: dict[str, int]  # every CheckInLog.Result, zeros included

    @property
    def seats(self) -> int:
        """Sum of the categories' quotas: what can be booked (not the venue capacity)."""
        return sum(t.capacity for t in self.ticket_types)

    @property
    def reserved(self) -> int:
        return sum(t.reserved_count for t in self.ticket_types)

    @property
    def checked_in(self) -> int:
        return sum(t.checked_in for t in self.ticket_types)


def event_stats(event: Event) -> EventStats:
    """Occupancy per category and every check-in attempt, in three queries."""
    used = Q(reservations__ticket__status=Ticket.Status.USED)
    ticket_types = list(
        TicketType.objects.filter(event=event).annotate(
            checked_in=Count("reservations__ticket", filter=used)
        )
    )
    cancelled = Reservation.objects.filter(event=event, status=Reservation.Status.CANCELLED).count()
    scans = dict.fromkeys(CheckInLog.Result.values, 0)
    for row in CheckInLog.objects.filter(event=event).values("result").annotate(n=Count("pk")):
        scans[row["result"]] = row["n"]
    return EventStats(ticket_types=ticket_types, cancelled=cancelled, scans=scans)


def _per_event(queryset: QuerySet, event_path: str, aggregate) -> Coalesce:
    """One value per event from `queryset`, as a subquery.

    Annotating Sum("ticket_types__capacity") and Count("reservations__ticket") on the same
    queryset joins two one-to-many relations at once and multiplies the rows: each capacity
    would be added once per ticket, and each ticket counted once per category.
    """
    return Coalesce(
        Subquery(
            queryset.filter(**{event_path: OuterRef("pk")})
            .order_by()
            .values(event_path)
            .annotate(value=aggregate)
            .values("value")
        ),
        0,
    )


@dataclass(frozen=True)
class OrganizationStats:
    active_events: int
    seats: int
    reserved: int
    checked_in: int
    upcoming: list[Event]  # annotated with `seats`, `reserved` and `checked_in`


def organization_stats(
    organization: Organization, now: datetime, upcoming_limit: int = 10
) -> OrganizationStats:
    """Totals over the organization's published events (finished ones included), plus the
    next ones with their occupancy. Drafts and cancelled events are left out."""
    published = Event.objects.filter(organization=organization, status=Event.Status.PUBLISHED)
    seats = TicketType.objects.filter(event__in=published).aggregate(
        seats=Coalesce(Sum("capacity"), 0), reserved=Coalesce(Sum("reserved_count"), 0)
    )
    used = Ticket.objects.filter(status=Ticket.Status.USED)
    upcoming = (
        published.filter(end_at__gt=now)
        .annotate(
            seats=_per_event(TicketType.objects.all(), "event", Sum("capacity")),
            reserved=_per_event(TicketType.objects.all(), "event", Sum("reserved_count")),
            checked_in=_per_event(used, "reservation__event", Count("pk")),
        )
        .order_by("start_at")
    )
    return OrganizationStats(
        active_events=published.filter(end_at__gt=now).count(),
        seats=seats["seats"],
        reserved=seats["reserved"],
        checked_in=used.filter(reservation__event__in=published).count(),
        upcoming=list(upcoming[:upcoming_limit]),
    )
