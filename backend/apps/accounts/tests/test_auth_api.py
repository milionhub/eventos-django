import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

COOKIE = settings.REFRESH_COOKIE["key"]
PASSWORD = "Concierto-2026"


@pytest.fixture
def user() -> User:
    return UserFactory(email="ana@example.com", password=PASSWORD)


def login(api_client, email="ana@example.com", password=PASSWORD):
    return api_client.post(reverse("auth-login"), {"email": email, "password": password})


# --- register ---------------------------------------------------------------


def test_register_creates_account_without_exposing_password(api_client):
    response = api_client.post(
        reverse("auth-register"),
        {"email": "Ana@Example.com", "password": PASSWORD, "first_name": "Ana"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "email": "ana@example.com",
        "first_name": "Ana",
        "last_name": "",
    }
    assert User.objects.get(email="ana@example.com").check_password(PASSWORD)


def test_register_rejects_duplicate_email(api_client, user):
    response = api_client.post(
        reverse("auth-register"), {"email": "ANA@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


@pytest.mark.parametrize("password", ["123", "password", "ana@example.com"])
def test_register_rejects_weak_passwords(api_client, password):
    response = api_client.post(
        reverse("auth-register"), {"email": "ana@example.com", "password": password}
    )

    assert response.status_code == 400
    assert "password" in response.json()
    assert not User.objects.exists()


def test_register_is_throttled(api_client, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"register": "2/hour"})

    statuses = [
        api_client.post(
            reverse("auth-register"), {"email": f"spam{n}@example.com", "password": PASSWORD}
        ).status_code
        for n in range(3)
    ]

    assert statuses == [201, 201, 429]
    assert User.objects.count() == 2


# --- login ------------------------------------------------------------------


def test_login_returns_access_token_and_sets_refresh_cookie(api_client, user):
    response = login(api_client, email="ANA@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["access"]
    assert body["user"]["email"] == "ana@example.com"
    assert "refresh" not in body  # the refresh token never reaches JavaScript

    cookie = response.cookies[COOKIE]
    assert cookie.value
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/api/v1/auth/"


def test_login_with_wrong_password_fails(api_client, user):
    response = login(api_client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert COOKIE not in response.cookies


def test_login_is_throttled(api_client, user):
    statuses = [login(api_client, password="wrong-password").status_code for _ in range(11)]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_login_throttle_ignores_a_forged_x_forwarded_for(api_client, user):
    """The client writes that header: trusting it would give every attempt a fresh quota."""
    statuses = [
        api_client.post(
            reverse("auth-login"),
            {"email": "ana@example.com", "password": "wrong-password"},
            HTTP_X_FORWARDED_FOR=f"203.0.113.{attempt}",
        ).status_code
        for attempt in range(11)
    ]

    assert statuses[10] == 429


# --- me ---------------------------------------------------------------------


def test_me_returns_the_authenticated_user(api_client, user):
    access = login(api_client).json()["access"]

    response = api_client.get(reverse("auth-me"), HTTP_AUTHORIZATION=f"Bearer {access}")

    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"


def test_me_requires_authentication(api_client):
    assert api_client.get(reverse("auth-me")).status_code == 401


# --- refresh ----------------------------------------------------------------


def test_refresh_rotates_the_cookie_and_returns_a_new_access_token(api_client, user):
    old_refresh = login(api_client).cookies[COOKIE].value

    response = api_client.post(reverse("auth-refresh"))  # the client sends the cookie

    assert response.status_code == 200
    assert response.json()["access"]
    assert response.json()["user"]["email"] == "ana@example.com"
    assert response.cookies[COOKIE].value != old_refresh


def test_refresh_token_cannot_be_reused_after_rotation(api_client, user):
    old_refresh = login(api_client).cookies[COOKIE].value
    api_client.post(reverse("auth-refresh"))

    api_client.cookies[COOKIE] = old_refresh
    response = api_client.post(reverse("auth-refresh"))

    assert response.status_code == 401
    assert response.json()["code"] == "session_expired"


def test_refresh_is_throttled(api_client, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"refresh": "2/min"})

    statuses = [api_client.post(reverse("auth-refresh")).status_code for _ in range(3)]

    assert statuses == [401, 401, 429]


def test_refresh_without_cookie_fails(api_client):
    response = api_client.post(reverse("auth-refresh"))

    assert response.status_code == 401
    assert response.json()["code"] == "session_expired"


def test_refresh_fails_for_disabled_users(api_client, user):
    login(api_client)
    User.objects.filter(pk=user.pk).update(is_active=False)

    assert api_client.post(reverse("auth-refresh")).status_code == 401


# --- logout -----------------------------------------------------------------


def test_logout_revokes_the_refresh_token_and_clears_the_cookie(api_client, user):
    refresh = login(api_client).cookies[COOKIE].value

    response = api_client.post(reverse("auth-logout"))

    assert response.status_code == 204
    assert response.cookies[COOKIE].value == ""  # deleted
    api_client.cookies[COOKIE] = refresh
    assert api_client.post(reverse("auth-refresh")).status_code == 401


def test_logout_without_session_is_harmless(api_client):
    assert api_client.post(reverse("auth-logout")).status_code == 204
