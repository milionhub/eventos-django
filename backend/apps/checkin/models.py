from django.conf import settings
from django.db import models

from apps.events.models import Event
from apps.ticketing.models import Ticket


class CheckInLog(models.Model):
    """Every scan attempt, successful or not (RN-31). Rows are only ever inserted."""

    class Result(models.TextChoices):
        VALID = "VALID", "Válida"
        ALREADY_USED = "ALREADY_USED", "Ya utilizada"
        CANCELLED = "CANCELLED", "Cancelada"
        NOT_FOUND = "NOT_FOUND", "No existe"
        WRONG_EVENT = "WRONG_EVENT", "De otro evento"
        EVENT_NOT_ACTIVE = "EVENT_NOT_ACTIVE", "Fuera de horario"
        UNAUTHORIZED = "UNAUTHORIZED", "Sin permiso"

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="checkin_logs")
    # Null when the token matches no ticket. The scanned text itself is never stored:
    # it could be anything, and keeping arbitrary input is a liability.
    ticket = models.ForeignKey(
        Ticket, on_delete=models.PROTECT, null=True, blank=True, related_name="checkin_logs"
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="checkin_logs"
    )
    result = models.CharField(max_length=20, choices=Result.choices)
    checked_at = models.DateTimeField()

    class Meta:
        ordering = ["-checked_at"]
        indexes = [models.Index(fields=["event", "checked_at"], name="checkin_log_by_event")]

    def __str__(self) -> str:
        return f"{self.event} · {self.result} · {self.checked_at:%H:%M:%S}"
