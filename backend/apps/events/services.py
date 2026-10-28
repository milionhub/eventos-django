from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.core.slugs import unique_slug
from apps.events.models import Event
from apps.organizations.models import Organization

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
