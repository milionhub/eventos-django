from uuid import UUID

from apps.accounts.models import User
from apps.ticketing.models import Reservation


def reservation_of(user: User, reservation_id: UUID) -> Reservation | None:
    """Only the user's own reservations: someone else's id finds nothing (→ 404)."""
    return (
        Reservation.objects.filter(user=user, pk=reservation_id)
        .select_related("event", "ticket_type", "ticket")
        .first()
    )
