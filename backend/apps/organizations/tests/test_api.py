import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.organizations.models import Membership, Organization
from apps.organizations.tests.factories import MembershipFactory, OrganizationFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def org() -> Organization:
    return OrganizationFactory(slug="sala-apolo")


def member(org: Organization, role: str) -> Membership:
    return MembershipFactory(organization=org, role=role)


# --- my organizations ----------------------------------------------------------


def test_list_shows_only_my_organizations_with_my_role(org):
    me = member(org, Role.MANAGER).user
    MembershipFactory(role=Role.OWNER)  # someone else's organization

    response = client_for(me).get(reverse("organizations"))

    assert response.status_code == 200
    assert [(o["organization"]["slug"], o["role"]) for o in response.json()] == [
        ("sala-apolo", "MANAGER")
    ]


def test_any_user_can_create_an_organization_and_owns_it():
    user = UserFactory()

    response = client_for(user).post(
        reverse("organizations"), {"name": "Sala Apolo", "description": "Conciertos"}
    )

    assert response.status_code == 201
    assert response.json()["role"] == "OWNER"
    assert response.json()["organization"]["slug"] == "sala-apolo"


def test_slug_cannot_be_chosen_by_the_client():
    response = client_for(UserFactory()).post(
        reverse("organizations"), {"name": "Sala Apolo", "slug": "otra"}
    )

    assert response.json()["organization"]["slug"] == "sala-apolo"


def test_session_user_includes_memberships(org):
    me = member(org, Role.STAFF).user

    response = client_for(me).get(reverse("auth-me"))

    assert response.json()["memberships"] == [
        {"organization_slug": "sala-apolo", "organization_name": org.name, "role": "STAFF"}
    ]


# --- permission matrix (requirements.md §4) -----------------------------------
# Every organization endpoint by every role. "404" means "looks like it does not exist".

ENDPOINTS = {
    "detail.get": ("get", "organization", None),
    "detail.patch": ("patch", "organization", {"name": "Nuevo nombre"}),
    "members.get": ("get", "members", None),
    "members.post": ("post", "members", {"email": "nuevo@example.com", "role": "STAFF"}),
    "member.patch": ("patch", "member", {"role": "MANAGER"}),
    "member.delete": ("delete", "member", None),
}

EXPECTED = {
    #                  OWNER  MANAGER  STAFF  outsider
    "detail.get":    (200,   200,     200,   404),
    "detail.patch":  (200,   403,     403,   404),
    "members.get":   (200,   403,     403,   404),
    "members.post":  (201,   403,     403,   404),
    "member.patch":  (200,   403,     403,   404),
    "member.delete": (204,   403,     403,   404),
}  # fmt: skip

CALLERS = ["OWNER", "MANAGER", "STAFF", "outsider"]


@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_permission_matrix(org, endpoint, caller):
    UserFactory(email="nuevo@example.com")
    member(org, Role.OWNER)  # so the caller is never the last owner
    target = member(org, Role.STAFF)
    if caller == "outsider":
        user = member(OrganizationFactory(), Role.OWNER).user  # owner elsewhere
    else:
        user = member(org, caller).user

    method, name, data = ENDPOINTS[endpoint]
    kwargs = {"org_slug": org.slug}
    if name == "member":
        kwargs["member_id"] = target.pk
    response = getattr(client_for(user), method)(reverse(name, kwargs=kwargs), data)

    assert response.status_code == EXPECTED[endpoint][CALLERS.index(caller)]


def test_unknown_organization_is_404_too(org):
    owner = member(org, Role.OWNER).user

    response = client_for(owner).get(reverse("organization", kwargs={"org_slug": "no-existe"}))

    assert response.status_code == 404


def test_requires_authentication(org):
    response = APIClient().get(reverse("organization", kwargs={"org_slug": org.slug}))

    assert response.status_code == 401


def test_cannot_touch_members_of_another_organization_through_my_own(org):
    owner = member(org, Role.OWNER).user
    foreign = MembershipFactory(role=Role.STAFF)

    response = client_for(owner).delete(
        reverse("member", kwargs={"org_slug": org.slug, "member_id": foreign.pk})
    )

    assert response.status_code == 404
    assert Membership.objects.filter(pk=foreign.pk).exists()


# --- business errors over HTTP -----------------------------------------------


def test_add_unknown_email_explains_why(org):
    owner = member(org, Role.OWNER).user

    response = client_for(owner).post(
        reverse("members", kwargs={"org_slug": org.slug}),
        {"email": "nadie@example.com", "role": "STAFF"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "user_not_registered"


def test_last_owner_cannot_demote_themselves(org):
    owner = member(org, Role.OWNER)

    response = client_for(owner.user).patch(
        reverse("member", kwargs={"org_slug": org.slug, "member_id": owner.pk}),
        {"role": "MANAGER"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "last_owner"
