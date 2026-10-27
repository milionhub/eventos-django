import pytest
from django.db import IntegrityError

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email_to_lowercase():
    user = User.objects.create_user(email="  Ana.Garcia@Example.COM ", password="secret-pass-1")

    assert user.email == "ana.garcia@example.com"
    assert user.check_password("secret-pass-1")
    assert not user.is_staff
    assert not user.is_superuser


def test_email_is_unique_regardless_of_case():
    User.objects.create_user(email="ana@example.com", password="x")

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="ANA@example.com", password="x")


def test_create_user_without_email_fails():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")


def test_create_superuser_sets_flags():
    admin = User.objects.create_superuser(email="admin@example.com", password="x")

    assert admin.is_staff
    assert admin.is_superuser


def test_user_has_no_username_field():
    assert User.USERNAME_FIELD == "email"
    assert "username" not in {field.name for field in User._meta.get_fields()}
