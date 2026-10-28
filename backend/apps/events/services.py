from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.core.slugs import unique_slug
from apps.events.models import Event, EventStaff, TicketType
from apps.organizations.models import Membership, Organization

Status = Event.Status


class InvalidDates(DomainError):
    code = "invalid_dates"
    default_detail = "La fecha de fin debe ser posterior a la de inicio."


class EventNotEditable(DomainError):
    code = "event_not_editable"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Este evento ya no se puede editar."


class PastDatesNotAllowed(DomainError):
    code = "past_dates"
    default_detail = "Un evento publicado solo puede moverse a fechas futuras."


class CapacityBelowAllocated(DomainError):
    code = "capacity_below_allocated"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El aforo no puede ser menor que la suma de los cupos de sus entradas."


class InvalidTransition(DomainError):
    code = "invalid_transition"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El evento no admite este cambio de estado."


class EventNotPublishable(DomainError):
    code = "not_publishable"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El evento no cumple los requisitos para publicarse."


def _has_finished(event: Event, now: datetime) -> bool:
    # RN-08: only a published event "finishes"; a draft with past dates can still be fixed.
    return event.status == Status.PUBLISHED and event.end_at < now


def allocated_capacity(event: Event) -> int:
    """Seats already handed out to ticket categories (RN-13)."""
    return event.ticket_types.aggregate(total=Sum("capacity"))["total"] or 0


def publish_blockers(event: Event, *, now: datetime | None = None) -> list[str]:
    """What is missing to publish (RN-09), in words for the organizer. Empty = publishable."""
    now = now or timezone.now()
    blockers = []
    if event.start_at <= now:
        blockers.append("La fecha de inicio debe ser futura.")
    if event.end_at <= event.start_at:
        blockers.append("La fecha de fin debe ser posterior a la de inicio.")
    if not event.ticket_types.exists():
        blockers.append("Añade al menos una categoría de entrada.")
    return blockers


def create_event(
    *,
    organization: Organization,
    user: User,
    title: str,
    location: str,
    start_at: datetime,
    end_at: datetime,
    capacity: int,
    description: str = "",
    image_url: str = "",
) -> Event:
    """New events always start as drafts (RN-07)."""
    if end_at <= start_at:
        raise InvalidDates()
    return Event.objects.create(
        organization=organization,
        created_by=user,
        title=title,
        slug=unique_slug(Event, title, max_length=220),
        description=description,
        location=location,
        image_url=image_url,
        start_at=start_at,
        end_at=end_at,
        capacity=capacity,
    )


EDITABLE_FIELDS = {
    "title",
    "description",
    "location",
    "image_url",
    "start_at",
    "end_at",
    "capacity",
}


@transaction.atomic
def update_event(*, event: Event, now: datetime | None = None, **changes) -> Event:
    """Edit an event (RN-11). The slug never changes, so shared links keep working."""
    now = now or timezone.now()
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"Campos no editables: {sorted(unknown)}")

    event = Event.objects.select_for_update().get(pk=event.pk)
    if event.status == Status.CANCELLED or _has_finished(event, now):
        raise EventNotEditable()

    start_at = changes.get("start_at", event.start_at)
    end_at = changes.get("end_at", event.end_at)
    if end_at <= start_at:
        raise InvalidDates()
    dates_changed = start_at != event.start_at or end_at != event.end_at
    if event.status == Status.PUBLISHED and dates_changed and start_at <= now:
        raise PastDatesNotAllowed()

    # RN-13 (and so RN-11): categories can never add up to more than the event's capacity.
    if "capacity" in changes and changes["capacity"] < allocated_capacity(event):
        raise CapacityBelowAllocated()

    for field, value in changes.items():
        setattr(event, field, value)
    event.save()
    return event


@transaction.atomic
def publish_event(*, event: Event, now: datetime | None = None) -> Event:
    """DRAFT → PUBLISHED (RN-07, RN-09). Row-locked so two clicks cannot race."""
    now = now or timezone.now()
    event = Event.objects.select_for_update().get(pk=event.pk)
    if event.status != Status.DRAFT:
        raise InvalidTransition("Solo se pueden publicar eventos en borrador.")
    blockers = publish_blockers(event, now=now)
    if blockers:
        raise EventNotPublishable(" ".join(blockers))
    event.status = Status.PUBLISHED
    event.published_at = now
    event.save(update_fields=["status", "published_at", "updated_at"])
    return event


@transaction.atomic
def cancel_event(*, event: Event, now: datetime | None = None) -> Event:
    """DRAFT or PUBLISHED → CANCELLED. There is no way back (RN-07).

    RN-10 (cancelling its reservations and tickets) is added with ticketing in Phase 3.
    """
    now = now or timezone.now()
    event = Event.objects.select_for_update().get(pk=event.pk)
    if event.status == Status.CANCELLED:
        raise InvalidTransition("El evento ya está cancelado.")
    if _has_finished(event, now):
        raise InvalidTransition("No se puede cancelar un evento que ya ha terminado.")
    event.status = Status.CANCELLED
    event.cancelled_at = now
    event.save(update_fields=["status", "cancelled_at", "updated_at"])
    return event


# --- Ticket types (RN-12 to RN-15) ------------------------------------------------------


class CapacityExceeded(DomainError):
    code = "capacity_exceeded"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La suma de los cupos de las entradas superaría el aforo del evento."


class CapacityBelowReserved(DomainError):
    code = "capacity_below_reserved"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El cupo no puede ser menor que las entradas ya reservadas."


class DuplicateTicketTypeName(DomainError):
    code = "duplicate_name"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ya hay una categoría de entrada con ese nombre en este evento."


class TicketTypeInUse(DomainError):
    code = "ticket_type_in_use"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "No se puede borrar una categoría que tiene reservas."


class LastTicketType(DomainError):
    code = "last_ticket_type"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Un evento publicado necesita al menos una categoría de entrada."


def _lock_editable_event(event_id: int, now: datetime) -> Event:
    """Lock the event row: category changes on one event are serialized (RN-13 under load)."""
    event = Event.objects.select_for_update().get(pk=event_id)
    if event.status == Status.CANCELLED or _has_finished(event, now):
        raise EventNotEditable()
    return event


def _save_ticket_type(ticket_type: TicketType) -> TicketType:
    try:
        with transaction.atomic():
            ticket_type.save()
    except IntegrityError as exc:  # unique (event, name)
        raise DuplicateTicketTypeName() from exc
    return ticket_type


@transaction.atomic
def create_ticket_type(
    *, event: Event, name: str, capacity: int, description: str = "", now: datetime | None = None
) -> TicketType:
    event = _lock_editable_event(event.pk, now or timezone.now())
    if allocated_capacity(event) + capacity > event.capacity:
        raise CapacityExceeded()
    return _save_ticket_type(
        TicketType(event=event, name=name, description=description, capacity=capacity)
    )


@transaction.atomic
def update_ticket_type(
    *, ticket_type: TicketType, now: datetime | None = None, **changes
) -> TicketType:
    event = _lock_editable_event(ticket_type.event_id, now or timezone.now())
    ticket_type = TicketType.objects.select_for_update().get(pk=ticket_type.pk)
    if "capacity" in changes:
        capacity = changes["capacity"]
        if capacity < ticket_type.reserved_count:  # RN-14
            raise CapacityBelowReserved()
        others = allocated_capacity(event) - ticket_type.capacity
        if others + capacity > event.capacity:  # RN-13
            raise CapacityExceeded()
    for field in ("name", "description", "capacity"):
        if field in changes:
            setattr(ticket_type, field, changes[field])
    return _save_ticket_type(ticket_type)


@transaction.atomic
def delete_ticket_type(*, ticket_type: TicketType, now: datetime | None = None) -> None:
    event = _lock_editable_event(ticket_type.event_id, now or timezone.now())
    # RN-15. Today reserved_count is the only trace of reservations; in Phase 3 this also
    # checks historical (cancelled) reservations, which keep the category referenced.
    if TicketType.objects.get(pk=ticket_type.pk).reserved_count > 0:
        raise TicketTypeInUse()
    if event.status == Status.PUBLISHED and event.ticket_types.count() == 1:
        raise LastTicketType()
    ticket_type.delete()


# --- Staff (RN-28) ----------------------------------------------------------------------


class NotAMember(DomainError):
    code = "not_a_member"
    default_detail = "Solo se puede asignar a miembros de la organización."


class AlreadyAssigned(DomainError):
    code = "already_assigned"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Esa persona ya está asignada a este evento."


def assign_staff(*, event: Event, user_id: int) -> EventStaff:
    """Assign a member of the event's organization to validate tickets at it."""
    membership = Membership.objects.filter(
        organization_id=event.organization_id, user_id=user_id
    ).first()
    if membership is None:
        raise NotAMember()
    try:
        with transaction.atomic():
            return EventStaff.objects.create(event=event, user_id=user_id)
    except IntegrityError as exc:
        raise AlreadyAssigned() from exc


def unassign_staff(*, assignment: EventStaff) -> None:
    assignment.delete()
