from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

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


# --- Sessions (ADR-0003, ADR-0009) ----------------------------------------------------------


class SessionExpired(Exception):
    pass


@dataclass(frozen=True)
class RefreshedSession:
    user: User
    access: str
    refresh: str


def _replaced_key(jti: str) -> str:
    return f"refresh-replaced:{jti}"


def _logged_out_key(user_id: str) -> str:
    return f"refresh-logged-out:{user_id}"


def _decode(token: str) -> dict | None:
    """The claims of a genuine, unexpired refresh token, blacklisted or not."""
    try:
        payload = token_backend.decode(token, verify=True)
    except TokenBackendError:
        return None
    return payload if payload.get("token_type") == "refresh" else None


def refresh_session(*, token: str, now: datetime | None = None) -> RefreshedSession:
    """Swap a refresh token for a new one (rotation), raising SessionExpired if it cannot be.

    If the browser navigates away while this runs, the server has already blacklisted the old
    token but the browser never receives the new one, and the session would be lost. So a
    token replaced moments ago still works for REFRESH_REUSE_GRACE_SECONDS (ADR-0009).
    """
    now = now or timezone.now()
    payload = _decode(token)
    if payload is None:
        raise SessionExpired()

    jti = payload["jti"]
    # Only a token still in use gets the mark. Marking one that is already blacklisted would
    # let an old or logged-out token grant itself a new grace period.
    if not BlacklistedToken.objects.filter(token__jti=jti).exists():
        # Before rotating, so that a simultaneous request never sees it blacklisted but unmarked.
        cache.set(_replaced_key(jti), now.timestamp(), settings.REFRESH_REUSE_GRACE_SECONDS)
        serializer = TokenRefreshSerializer(data={"refresh": token})
        # Expired or inactive user (AuthenticationFailed), empty (ValidationError), or blacklisted
        # by a simultaneous request (a bare TokenError in simplejwt 5.5).
        with suppress(ValidationError, AuthenticationFailed, TokenError):
            serializer.is_valid(raise_exception=True)
            refresh = serializer.validated_data["refresh"]
            return RefreshedSession(
                user=User.objects.get(pk=payload["user_id"]),
                access=serializer.validated_data["access"],
                refresh=refresh,
            )
    return _reissue_replaced_token(payload, now)


def _reissue_replaced_token(payload: dict, now: datetime) -> RefreshedSession:
    replaced_at = cache.get(_replaced_key(payload["jti"]))
    if (
        replaced_at is None
        or now.timestamp() - replaced_at > settings.REFRESH_REUSE_GRACE_SECONDS
        or cache.get(_logged_out_key(payload["user_id"]))
    ):
        raise SessionExpired()
    user = User.objects.filter(pk=payload["user_id"], is_active=True).first()
    if user is None:
        raise SessionExpired()
    refresh = RefreshToken.for_user(user)
    return RefreshedSession(user=user, access=str(refresh.access_token), refresh=str(refresh))


def end_session(*, token: str) -> None:
    """Log out: revoke this token, and no token of this user may use the grace period."""
    payload = _decode(token)
    if payload is not None:
        cache.set(_logged_out_key(payload["user_id"]), True, settings.REFRESH_REUSE_GRACE_SECONDS)
    with suppress(TokenError):  # already invalid: nothing to revoke
        RefreshToken(token).blacklist()
