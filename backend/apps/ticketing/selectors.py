from uuid import UUID

from django.db.models import QuerySet

from apps.accounts.models import User
from apps.ticketing.models import Reservation, Ticket


def reservation_of(user: User, reservation_id: UUID) -> Reservation | None:
    """Only the user's own reservations: someone else's id finds nothing (→ 404)."""
    return (
        Reservation.objects.filter(user=user, pk=reservation_id)
        .select_related("event", "ticket_type", "ticket")
        .first()
    )


def tickets_of(user: User) -> QuerySet[Ticket]:
    """All the user's tickets, any status, soonest event first."""
    return (
        Ticket.objects.filter(reservation__user=user)
        .select_related(
            "reservation", "reservation__event__organization", "reservation__ticket_type"
        )
        .order_by("reservation__event__start_at", "-issued_at")
    )


def ticket_of(user: User, ticket_id: UUID) -> Ticket | None:
    """Only the user's own tickets: someone else's id finds nothing (→ 404)."""
    return tickets_of(user).filter(pk=ticket_id).first()
