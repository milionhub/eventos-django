"""ADR-0009: a refresh token replaced moments ago still works; nothing else does."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.services import SessionExpired, end_session, refresh_session
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def token(user) -> str:
    return str(RefreshToken.for_user(user))


def test_rotation_gives_a_new_token_that_works(token):
    new = refresh_session(token=token)
    assert new.refresh != token
    assert refresh_session(token=new.refresh).user == new.user


def test_a_replaced_token_works_within_the_grace_period(token):
    start = timezone.now()
    refresh_session(token=token, now=start)

    again = refresh_session(token=token, now=start + timedelta(seconds=29))

    assert again.refresh != token
    assert refresh_session(token=again.refresh).user == again.user


def test_a_replaced_token_stops_working_after_the_grace_period(token):
    start = timezone.now()
    refresh_session(token=token, now=start)

    with pytest.raises(SessionExpired):
        refresh_session(token=token, now=start + timedelta(seconds=31))


def test_reusing_a_token_does_not_extend_its_grace_period(token):
    start = timezone.now()
    refresh_session(token=token, now=start)
    refresh_session(token=token, now=start + timedelta(seconds=25))

    with pytest.raises(SessionExpired):
        refresh_session(token=token, now=start + timedelta(seconds=31))


def test_a_token_revoked_by_logout_gets_no_grace_period(token):
    end_session(token=token)

    with pytest.raises(SessionExpired):
        refresh_session(token=token)


def test_after_logout_an_older_replaced_token_cannot_reopen_the_session(token):
    new = refresh_session(token=token)
    end_session(token=new.refresh)

    with pytest.raises(SessionExpired):
        refresh_session(token=token)


def test_an_inactive_user_gets_no_grace_period(user, token):
    refresh_session(token=token)
    user.is_active = False
    user.save()

    with pytest.raises(SessionExpired):
        refresh_session(token=token)


def test_an_inactive_user_cannot_rotate_either(user, token):
    user.is_active = False
    user.save()

    with pytest.raises(SessionExpired):
        refresh_session(token=token)


def test_an_expired_token_is_rejected(user):
    expired = RefreshToken.for_user(user)
    expired.set_exp(lifetime=-timedelta(seconds=1))

    with pytest.raises(SessionExpired):
        refresh_session(token=str(expired))


@pytest.mark.parametrize("value", ["", "not-a-token"])
def test_garbage_is_rejected(value):
    with pytest.raises(SessionExpired):
        refresh_session(token=value)


def test_a_tampered_token_is_rejected(token):
    with pytest.raises(SessionExpired):
        refresh_session(token=token[:-2] + ("aa" if not token.endswith("aa") else "bb"))


def test_an_access_token_is_not_a_refresh_token(user):
    with pytest.raises(SessionExpired):
        refresh_session(token=str(AccessToken.for_user(user)))


def test_logging_out_with_an_invalid_token_is_harmless():
    end_session(token="not-a-token")
