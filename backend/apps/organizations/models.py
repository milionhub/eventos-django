from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Organization(TimeStampedModel):
    name = models.CharField("nombre", max_length=120)
    # Generated from the name on creation and never changed, so URLs stay stable.
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField("descripción", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Propietario"
        MANAGER = "MANAGER", "Gestor"
        STAFF = "STAFF", "Personal de acceso"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField("rol", max_length=10, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="unique_membership_per_organization"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.organization} ({self.role})"
