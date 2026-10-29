from uuid import UUID

from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.events.models import Event
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


# --- Organizer side: the attendee list (requirements.md R5) ------------------------------------


def attendees_of(
    event: Event, *, q: str = "", ticket_status: str | None = None
) -> QuerySet[Reservation]:
    """Every reservation of the event, cancelled ones included, newest first.

    `q` matches name or email word by word, so «ana gómez» finds Ana Gómez whichever field
    each word is in. `ticket_status` narrows to VALID (still to come in), USED or CANCELLED.
    """
    reservations = Reservation.objects.filter(event=event)
    for word in q.split():
        reservations = reservations.filter(
            Q(user__first_name__icontains=word)
            | Q(user__last_name__icontains=word)
            | Q(user__email__icontains=word)
        )
    if ticket_status:
        reservations = reservations.filter(ticket__status=ticket_status)
    return reservations.select_related("user", "ticket_type", "ticket").order_by(
        "-created_at", "pk"
    )


def reservation_in(event: Event, reservation_id: UUID) -> Reservation | None:
    """A reservation of this event only: an id from another event finds nothing (→ 404)."""
    return Reservation.objects.filter(event=event, pk=reservation_id).first()
