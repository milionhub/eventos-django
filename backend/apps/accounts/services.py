from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from rest_framework import status

from apps.accounts.models import User
from apps.core.exceptions import DomainError


class EmailAlreadyRegistered(DomainError):
    code = "email_taken"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ya existe una cuenta con este email."


class InvalidCredentials(DomainError):
    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Email o contraseña incorrectos."


def register_user(*, email: str, password: str, first_name: str = "", last_name: str = "") -> User:
    """Create an account. Emails are unique regardless of case (RN-01)."""
    email = User.objects.normalize_email(email)
    if User.objects.filter(email=email).exists():
        raise EmailAlreadyRegistered()
    try:
        # The unique constraint is the real guard if two sign-ups race.
        with transaction.atomic():
            return User.objects.create_user(
                email=email, password=password, first_name=first_name, last_name=last_name
            )
    except IntegrityError as exc:
        raise EmailAlreadyRegistered() from exc


def authenticate_user(*, request: HttpRequest | None, email: str, password: str) -> User:
    """Return the active user for these credentials, matching the email case-insensitively."""
    user = authenticate(request, email=User.objects.normalize_email(email), password=password)
    if user is None:
        # Same error for unknown email, wrong password or inactive account: no user enumeration.
        raise InvalidCredentials()
    return user
