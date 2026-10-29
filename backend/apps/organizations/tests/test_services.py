import pytest

from apps.accounts.tests.factories import UserFactory
from apps.core.slugs import unique_slug
from apps.organizations.models import Membership, Organization
from apps.organizations.services import (
    AlreadyMember,
    LastOwner,
    UserNotRegistered,
    add_member,
    change_member_role,
    create_organization,
    remove_member,
    update_organization,
)
from apps.organizations.tests.factories import MembershipFactory, OrganizationFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role


# --- create / update ----------------------------------------------------------


def test_creator_becomes_owner():
    user = UserFactory()

    organization = create_organization(user=user, name="Sala Apolo", description="Barcelona")

    assert organization.slug == "sala-apolo"
    assert Membership.objects.get(organization=organization).user == user
    assert Membership.objects.get(organization=organization).role == Role.OWNER


def test_slugs_are_unique():
    user = UserFactory()

    first = create_organization(user=user, name="Sala Apolo")
    second = create_organization(user=user, name="Sala Apolo")

    assert (first.slug, second.slug) == ("sala-apolo", "sala-apolo-2")


def test_unique_slug_respects_max_length_with_suffix():
    OrganizationFactory(slug="a" * 10)

    assert unique_slug(Organization, "a" * 20, max_length=10) == "aaaaaaaa-2"


def test_update_keeps_the_slug():
    organization = create_organization(user=UserFactory(), name="Sala Apolo")

    update_organization(organization=organization, name="Apolo Club")

    organization.refresh_from_db()
    assert (organization.name, organization.slug) == ("Apolo Club", "sala-apolo")


def test_update_only_what_is_sent():
    organization = create_organization(user=UserFactory(), name="Sala Apolo")

    update_organization(organization=organization, description="Conciertos desde 1904")

    organization.refresh_from_db()
    assert (organization.name, organization.description) == ("Sala Apolo", "Conciertos desde 1904")


# --- members ------------------------------------------------------------------


def test_add_member_by_email_regardless_of_case():
    organization = OrganizationFactory()
    user = UserFactory(email="luis@example.com")

    membership = add_member(organization=organization, email="LUIS@example.com", role=Role.STAFF)

    assert (membership.user, membership.role) == (user, Role.STAFF)


def test_add_member_requires_a_registered_user():
    with pytest.raises(UserNotRegistered):
        add_member(organization=OrganizationFactory(), email="nadie@example.com", role=Role.STAFF)


def test_add_member_rejects_existing_members():
    membership = MembershipFactory(role=Role.STAFF)

    with pytest.raises(AlreadyMember):
        add_member(
            organization=membership.organization, email=membership.user.email, role=Role.MANAGER
        )


def test_change_role():
    MembershipFactory(role=Role.OWNER)  # another organization's owner: irrelevant
    membership = MembershipFactory(role=Role.STAFF)

    change_member_role(membership=membership, role=Role.MANAGER)

    membership.refresh_from_db()
    assert membership.role == Role.MANAGER


# --- RN-04: always at least one owner ----------------------------------------


def test_last_owner_cannot_be_demoted():
    owner = MembershipFactory(role=Role.OWNER)

    with pytest.raises(LastOwner):
        change_member_role(membership=owner, role=Role.MANAGER)


def test_last_owner_cannot_be_removed():
    owner = MembershipFactory(role=Role.OWNER)

    with pytest.raises(LastOwner):
        remove_member(membership=owner)
    assert Membership.objects.filter(pk=owner.pk).exists()


def test_an_owner_can_step_down_if_another_owner_remains():
    owner = MembershipFactory(role=Role.OWNER)
    MembershipFactory(organization=owner.organization, role=Role.OWNER)

    change_member_role(membership=owner, role=Role.MANAGER)

    owner.refresh_from_db()
    assert owner.role == Role.MANAGER


def test_removing_non_owners_is_always_allowed():
    MembershipFactory(role=Role.OWNER)
    staff = MembershipFactory(role=Role.STAFF)

    remove_member(membership=staff)

    assert not Membership.objects.filter(pk=staff.pk).exists()
