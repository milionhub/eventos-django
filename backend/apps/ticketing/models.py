import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.events.models import Event, TicketType


class Reservation(TimeStampedModel):
    """One seat of one category for one user (RN-16). Never deleted, only cancelled."""

    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"

    # UUIDs: these ids appear in attendee URLs and must not be guessable.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservations"
    )
    # Denormalized from ticket_type so the partial unique constraint below can use it.
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="reservations")
    ticket_type = models.ForeignKey(
        TicketType, on_delete=models.PROTECT, related_name="reservations"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CONFIRMED)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # RN-17, enforced by PostgreSQL: at most one confirmed reservation per user and
            # event. A partial index, so cancelled reservations do not block booking again.
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=Q(status="CONFIRMED"),
                name="one_confirmed_reservation_per_event",
            ),
        ]
        indexes = [models.Index(fields=["event", "status"], name="reservation_by_event")]

    def __str__(self) -> str:
        return f"{self.user} · {self.ticket_type} ({self.status})"


class Ticket(models.Model):
    """The entry pass of a reservation. Its QR holds only `token` (RN-25, RN-26)."""

    class Status(models.TextChoices):
        VALID = "VALID", "Válida"
        USED = "USED", "Utilizada"
        CANCELLED = "CANCELLED", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # OneToOne today; a ForeignKey if reservations ever hold several tickets (ADR-0005).
    reservation = models.OneToOneField(Reservation, on_delete=models.PROTECT, related_name="ticket")
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.VALID)
    issued_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    def __str__(self) -> str:
        return f"Entrada {self.id} ({self.status})"
