import pytest

from apps.accounts.services import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    authenticate_user,
    register_user,
)
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_register_user_normalizes_email_and_hashes_password():
    user = register_user(email=" Ana@Example.COM ", password="Concierto-2026", first_name="Ana")

    assert user.email == "ana@example.com"
    assert user.first_name == "Ana"
    assert user.check_password("Concierto-2026")


def test_register_user_rejects_existing_email_regardless_of_case():
    UserFactory(email="ana@example.com")

    with pytest.raises(EmailAlreadyRegistered):
        register_user(email="ANA@example.com", password="Concierto-2026")


def test_authenticate_user_matches_email_case_insensitively():
    user = UserFactory(email="ana@example.com", password="Concierto-2026")

    assert (
        authenticate_user(request=None, email="ANA@Example.com", password="Concierto-2026") == user
    )


@pytest.mark.parametrize(
    ("email", "password", "is_active"),
    [
        ("ana@example.com", "wrong-password", True),  # wrong password
        ("nadie@example.com", "Concierto-2026", True),  # unknown email
        ("ana@example.com", "Concierto-2026", False),  # disabled account
    ],
)
def test_authenticate_user_fails_with_the_same_error(email, password, is_active):
    UserFactory(email="ana@example.com", password="Concierto-2026", is_active=is_active)

    with pytest.raises(InvalidCredentials):
        authenticate_user(request=None, email=email, password=password)
