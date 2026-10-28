import io
import uuid
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
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


def _lock_event_rows():
    """Events to lock with FOR NO KEY UPDATE, not plain FOR UPDATE.

    Inserting a reservation (or a category) checks its foreign key to the event, and that
    check takes a FOR KEY SHARE lock on the event row. FOR UPDATE conflicts with it, so a
    booking holding a category's row lock and an event change waiting for that same row
    would wait for each other forever: a deadlock (caught by test_concurrency). We never
    change an event's primary key, so the weaker NO KEY lock is enough: it still makes
    event changes wait for each other, but lets foreign key checks through.
    """
    return Event.objects.select_for_update(no_key=True)


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
        start_at=start_at,
        end_at=end_at,
        capacity=capacity,
    )


EDITABLE_FIELDS = {"title", "description", "location", "start_at", "end_at", "capacity"}


@transaction.atomic
def update_event(*, event: Event, now: datetime | None = None, **changes) -> Event:
    """Edit an event (RN-11). The slug never changes, so shared links keep working."""
    now = now or timezone.now()
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"Campos no editables: {sorted(unknown)}")

    event = _lock_event_rows().get(pk=event.pk)
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
    event = _lock_event_rows().get(pk=event.pk)
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
def cancel_event(*, event: Event, by: User | None = None, now: datetime | None = None) -> Event:
    """DRAFT or PUBLISHED → CANCELLED, with no way back (RN-07). Cancels every reservation
    and ticket not used yet and gives their seats back (RN-10).

    Against concurrent bookings: the categories' rows are locked *before* changing anything.
    `reserve()` increments a category with an UPDATE that takes the same row lock, so:
    - a booking that got there first makes us wait, commits, and is then cancelled below;
    - a booking that comes after waits for us, then re-reads the event, sees it cancelled
      and rolls its seat back.
    Either way no confirmed reservation survives on a cancelled event.
    """
    now = now or timezone.now()
    event = _lock_event_rows().get(pk=event.pk)
    if event.status == Status.CANCELLED:
        raise InvalidTransition("El evento ya está cancelado.")
    if _has_finished(event, now):
        raise InvalidTransition("No se puede cancelar un evento que ya ha terminado.")
    ticket_types = list(TicketType.objects.select_for_update().filter(event=event))

    event.status = Status.CANCELLED
    event.cancelled_at = now
    event.save(update_fields=["status", "cancelled_at", "updated_at"])

    # Imported here: ticketing builds on events, not the other way round.
    from apps.ticketing.models import Reservation, Ticket

    to_cancel = Reservation.objects.filter(
        event=event, status=Reservation.Status.CONFIRMED
    ).exclude(ticket__status=Ticket.Status.USED)  # a used ticket stays as it was (RN-10)
    Ticket.objects.filter(reservation__in=to_cancel).update(status=Ticket.Status.CANCELLED)
    to_cancel.update(
        status=Reservation.Status.CANCELLED, cancelled_at=now, cancelled_by=by, updated_at=now
    )
    # Seats left taken are exactly the confirmed reservations that remain (ADR-0004).
    for ticket_type in ticket_types:
        ticket_type.reserved_count = Reservation.objects.filter(
            ticket_type=ticket_type, status=Reservation.Status.CONFIRMED
        ).count()
        ticket_type.save(update_fields=["reserved_count", "updated_at"])
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
    event = _lock_event_rows().get(pk=event_id)
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
    # RN-15: any reservation, even a cancelled one, keeps the category in the history.
    from apps.ticketing.models import Reservation

    if (
        TicketType.objects.get(pk=ticket_type.pk).reserved_count > 0
        or Reservation.objects.filter(ticket_type=ticket_type).exists()
    ):
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


# --- Event image (ADR-0008) ------------------------------------------------------------------


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_WIDTH = 1600
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidImage(DomainError):
    code = "invalid_image"
    default_detail = "El archivo no es una imagen JPG, PNG o WebP válida."


class ImageTooLarge(DomainError):
    code = "image_too_large"
    default_detail = "La imagen no puede pesar más de 5 MB."


def _reencode(upload) -> ContentFile:
    """Check the upload really is an allowed image and rebuild it from its pixels as WebP.

    Re-encoding drops EXIF (a phone photo's GPS position), colour profiles and anything
    hidden in the file. Pillow refuses images over its decompression-bomb pixel limit.
    """
    try:
        with Image.open(upload) as probe:
            image_format = probe.format
            probe.verify()  # structure check; the image cannot be used after this
        upload.seek(0)
        with Image.open(upload) as image:
            image.load()
            image = ImageOps.exif_transpose(image)  # keep phone photos upright
            image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as exc:
        raise InvalidImage() from exc
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise InvalidImage()

    if image.width > MAX_IMAGE_WIDTH:
        height = round(image.height * MAX_IMAGE_WIDTH / image.width)
        image = image.resize((MAX_IMAGE_WIDTH, height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=82)
    return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4().hex}.webp")


@transaction.atomic
def set_event_image(*, event: Event, upload, now: datetime | None = None) -> Event:
    """Replace the event's image with a validated, re-encoded copy of `upload`."""
    event = _lock_editable_event(event.pk, now or timezone.now())
    if upload.size > MAX_IMAGE_BYTES:
        raise ImageTooLarge()
    content = _reencode(upload)
    previous = event.image.name
    event.image.save(content.name, content, save=False)
    event.save(update_fields=["image", "updated_at"])
    if previous:
        # Delete the old file only once the new one is committed.
        transaction.on_commit(lambda: event.image.storage.delete(previous))
    return event


@transaction.atomic
def remove_event_image(*, event: Event, now: datetime | None = None) -> Event:
    event = _lock_editable_event(event.pk, now or timezone.now())
    previous = event.image.name
    event.image = ""
    event.save(update_fields=["image", "updated_at"])
    if previous:
        transaction.on_commit(lambda: event.image.storage.delete(previous))
    return event
