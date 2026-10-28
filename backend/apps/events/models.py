from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.organizations.models import Organization


class Event(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PUBLISHED = "PUBLISHED", "Publicado"
        CANCELLED = "CANCELLED", "Cancelado"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="events")
    title = models.CharField("título", max_length=200)
    # Global and stable: the public URL is /events/<slug>.
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField("descripción", blank=True)
    location = models.CharField("ubicación", max_length=255)
    image_url = models.URLField("imagen", blank=True)  # no file uploads in the MVP
    start_at = models.DateTimeField("inicio")
    end_at = models.DateTimeField("fin")
    capacity = models.PositiveIntegerField("aforo")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_at__gt=F("start_at")), name="event_ends_after_start"
            ),
            models.CheckConstraint(condition=Q(capacity__gt=0), name="event_capacity_positive"),
        ]
        indexes = [
            models.Index(fields=["status", "start_at"], name="event_public_listing"),
            models.Index(fields=["organization", "start_at"], name="event_by_organization"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_finished(self) -> bool:
        """RN-08: "finished" is not stored, it is a published event whose end has passed."""
        return self.status == self.Status.PUBLISHED and self.end_at < timezone.now()


class TicketType(TimeStampedModel):
    """A ticket category (General, VIP...) with its own quota (RN-12)."""

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="ticket_types")
    name = models.CharField("nombre", max_length=80)
    description = models.CharField("descripción", max_length=255, blank=True)
    capacity = models.PositiveIntegerField("cupo")
    # Denormalized counter kept by the reservation service (ADR-0004).
    reserved_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "name"], name="unique_ticket_type_name"),
            # Last line of defence against overselling.
            models.CheckConstraint(
                condition=Q(reserved_count__lte=F("capacity")), name="ticket_type_not_oversold"
            ),
            models.CheckConstraint(
                condition=Q(reserved_count__gte=0), name="ticket_type_reserved_not_negative"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event} · {self.name}"
