"""Reservations (requirements.md §3.5, ADR-0004, ADR-0005).

`reserve()` never reads the counter and then writes it from Python: between the read and
the write another request could take the last seat. Instead a single conditional UPDATE
both checks and increments, and PostgreSQL makes concurrent UPDATEs of the same row wait
for each other, re-evaluating the WHERE with the latest value:

    UPDATE events_tickettype
       SET reserved_count = reserved_count + 1
     WHERE id = %s AND reserved_count < capacity

1 row → we got a seat; 0 rows → sold out. Everything runs in one transaction, so if
anything fails afterwards (a duplicate reservation, the event being cancelled meanwhile)
the increment is rolled back too.
"""

import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.events.models import Event, TicketType
from apps.ticketing.models import Reservation, Ticket


class TicketTypeNotFound(DomainError):
    code = "ticket_type_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Esta categoría de entrada no existe o no está disponible."


class EventNotBookable(DomainError):
    code = "event_not_bookable"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ya no se puede reservar para este evento."


class SoldOut(DomainError):
    code = "sold_out"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "No quedan plazas en esta categoría."


class AlreadyReserved(DomainError):
    code = "already_reserved"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ya tienes una reserva para este evento."


def _is_bookable(event: Event, now: datetime) -> bool:
    """RN-18: published and not started yet."""
    return event.status == Event.Status.PUBLISHED and event.start_at > now


@transaction.atomic
def reserve(*, user: User, ticket_type_id: int, now: datetime | None = None) -> Reservation:
    """Book one seat of a category and issue its ticket. Safe under any concurrency."""
    now = now or timezone.now()

    ticket_type = TicketType.objects.select_related("event").filter(pk=ticket_type_id).first()
    # Drafts and cancelled events are not public: their categories "do not exist".
    if ticket_type is None or ticket_type.event.status != Event.Status.PUBLISHED:
        raise TicketTypeNotFound()
    event = ticket_type.event
    if not _is_bookable(event, now):
        raise EventNotBookable()

    # Friendly fast path. The partial unique index below is what really guarantees RN-17.
    if Reservation.objects.filter(
        user=user, event=event, status=Reservation.Status.CONFIRMED
    ).exists():
        raise AlreadyReserved()

    # The seat itself: one atomic, conditional UPDATE (RN-19).
    got_seat = TicketType.objects.filter(
        pk=ticket_type.pk, reserved_count__lt=F("capacity")
    ).update(reserved_count=F("reserved_count") + 1)
    if not got_seat:
        raise SoldOut()

    # We now hold this category's row lock until commit. Re-read the event with a fresh
    # snapshot: if it was cancelled meanwhile, give the seat back (the rollback does it).
    if not Event.objects.filter(pk=event.pk, status=Event.Status.PUBLISHED).exists():
        raise EventNotBookable()

    try:
        with transaction.atomic():  # savepoint: the IntegrityError must not poison the outer one
            reservation = Reservation.objects.create(
                user=user, event=event, ticket_type=ticket_type
            )
    except IntegrityError as exc:
        # Same user, same event, at the same time (a double click): the database rejected
        # the second one. Raising rolls back the outer transaction and so the increment.
        raise AlreadyReserved() from exc

    Ticket.objects.create(reservation=reservation, token=secrets.token_urlsafe(32))
    return reservation


# --- Cancellations (requirements.md §3.6) ------------------------------------------------


class AlreadyCancelled(DomainError):
    code = "already_cancelled"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Esta reserva ya está cancelada."


class TicketAlreadyUsed(DomainError):
    code = "ticket_used"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La entrada ya se ha utilizado y no se puede cancelar."


class CancellationWindowClosed(DomainError):
    code = "cancellation_closed"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El plazo para cancelar esta reserva ha terminado."


def cancellation_deadline(event: Event) -> datetime:
    """RN-20: attendees can cancel until this moment."""
    return event.start_at - timedelta(hours=settings.CANCELLATION_DEADLINE_HOURS)


@transaction.atomic
def cancel_reservation(
    *,
    reservation: Reservation,
    cancelled_by: User,
    as_organizer: bool = False,
    now: datetime | None = None,
) -> Reservation:
    """Cancel a reservation and its ticket, giving the seat back (RN-20 to RN-24).

    `as_organizer` is decided by the caller after checking the role (RN-21): organizers
    may cancel until the event ends; attendees only their own, until the deadline.
    """
    now = now or timezone.now()
    # Lock the reservation: two cancellations at once must not free the seat twice.
    reservation = (
        Reservation.objects.select_for_update().select_related("event").get(pk=reservation.pk)
    )
    if reservation.status == Reservation.Status.CANCELLED:
        raise AlreadyCancelled()

    event = reservation.event
    if as_organizer:
        if event.end_at <= now:
            raise CancellationWindowClosed("El evento ya ha terminado.")
    else:
        if cancelled_by.pk != reservation.user_id:
            raise ValueError("Attendees can only cancel their own reservations.")
        if now > cancellation_deadline(event):
            raise CancellationWindowClosed(
                f"Solo se puede cancelar hasta {settings.CANCELLATION_DEADLINE_HOURS} h "
                "antes del inicio."
            )

    ticket = Ticket.objects.select_for_update().get(reservation=reservation)
    if ticket.status == Ticket.Status.USED:  # RN-22
        raise TicketAlreadyUsed()

    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_at = now
    reservation.cancelled_by = cancelled_by
    reservation.save(update_fields=["status", "cancelled_at", "cancelled_by", "updated_at"])
    ticket.status = Ticket.Status.CANCELLED
    ticket.save(update_fields=["status"])
    # RN-23: the seat goes back with the same kind of atomic UPDATE that took it.
    TicketType.objects.filter(pk=reservation.ticket_type_id).update(
        reserved_count=F("reserved_count") - 1
    )
    return reservation
