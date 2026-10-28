from django.db import IntegrityError, transaction
from rest_framework import status

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.core.slugs import unique_slug
from apps.events.models import EventStaff
from apps.organizations.models import Membership, Organization

Role = Membership.Role


class UserNotRegistered(DomainError):
    code = "user_not_registered"
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "No hay ninguna cuenta con ese email. Pídele que se registre primero."


class AlreadyMember(DomainError):
    code = "already_member"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Esa persona ya es miembro de la organización."


class LastOwner(DomainError):
    code = "last_owner"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La organización debe tener al menos un propietario."


@transaction.atomic
def create_organization(*, user: User, name: str, description: str = "") -> Organization:
    """Create an organization; its creator becomes the OWNER (RN-03)."""
    organization = Organization.objects.create(
        name=name,
        slug=unique_slug(Organization, name, max_length=140),
        description=description,
    )
    Membership.objects.create(user=user, organization=organization, role=Role.OWNER)
    return organization


def update_organization(
    *, organization: Organization, name: str | None = None, description: str | None = None
) -> Organization:
    """Edit name and description. The slug is kept so existing links keep working."""
    if name is not None:
        organization.name = name
    if description is not None:
        organization.description = description
    organization.save(update_fields=["name", "description", "updated_at"])
    return organization


def add_member(*, organization: Organization, email: str, role: str) -> Membership:
    """Add a registered user by email (RN-05: no email invitations in the MVP)."""
    user = User.objects.filter(email=User.objects.normalize_email(email)).first()
    if user is None:
        raise UserNotRegistered()
    try:
        with transaction.atomic():
            return Membership.objects.create(user=user, organization=organization, role=role)
    except IntegrityError as exc:  # unique (user, organization)
        raise AlreadyMember() from exc


def _ensure_another_owner_remains(membership: Membership) -> None:
    """RN-04. Must run inside a transaction.

    Locks every OWNER row of the organization before counting, so two owners demoting
    or removing each other at the same time are serialized: the second one sees the
    first change and is rejected instead of leaving the organization without owners.
    """
    owners = list(
        Membership.objects.select_for_update()
        .filter(organization_id=membership.organization_id, role=Role.OWNER)
        .values_list("pk", flat=True)
    )
    if membership.pk in owners and len(owners) == 1:
        raise LastOwner()


@transaction.atomic
def change_member_role(*, membership: Membership, role: str) -> Membership:
    if membership.role == Role.OWNER and role != Role.OWNER:
        _ensure_another_owner_remains(membership)
    membership.role = role
    membership.save(update_fields=["role"])
    return membership


@transaction.atomic
def remove_member(*, membership: Membership) -> None:
    if membership.role == Role.OWNER:
        _ensure_another_owner_remains(membership)
    # Whoever leaves the organization stops working at its events too.
    EventStaff.objects.filter(
        user_id=membership.user_id, event__organization_id=membership.organization_id
    ).delete()
    membership.delete()
