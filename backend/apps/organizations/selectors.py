from django.db.models import QuerySet

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization


def memberships_for_user(user: User) -> QuerySet[Membership]:
    """The user's memberships with their organization, for "my organizations" and /me."""
    return (
        Membership.objects.filter(user=user)
        .select_related("organization")
        .order_by("organization__name")
    )


def membership_for(user: User, org_slug: str) -> Membership | None:
    return (
        Membership.objects.filter(user=user, organization__slug=org_slug)
        .select_related("organization")
        .first()
    )


def members_of(organization: Organization) -> QuerySet[Membership]:
    return Membership.objects.filter(organization=organization).select_related("user")
