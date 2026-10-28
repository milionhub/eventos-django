from apps.events.models import Event, TicketType
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.ticketing.models import Reservation


def bookable_ticket_type(**kwargs) -> TicketType:
    """A category of a published event one week from now (factory defaults)."""
    return TicketTypeFactory(event=EventFactory(status=Event.Status.PUBLISHED), **kwargs)


def assert_counters_match_reservations() -> None:
    """ADR-0004: the denormalized counter must always equal the confirmed reservations."""
    for ticket_type in TicketType.objects.all():
        confirmed = Reservation.objects.filter(
            ticket_type=ticket_type, status=Reservation.Status.CONFIRMED
        ).count()
        assert ticket_type.reserved_count == confirmed, (
            f"{ticket_type}: reserved_count={ticket_type.reserved_count}, confirmed={confirmed}"
        )
