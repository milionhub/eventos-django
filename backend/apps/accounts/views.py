"""Auth endpoints (ADR-0003).

The access token travels in the response body and Angular keeps it in memory.
The refresh token never reaches JavaScript: it lives in an httpOnly cookie scoped
to /api/v1/auth/, so these views read and write it themselves (simplejwt's stock
views expect it in the body).
"""

from contextlib import suppress

from django.conf import settings
from django.contrib.auth.models import update_last_login
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import services
from apps.accounts.models import User
from apps.accounts.serializers import (
    AuthSessionSerializer,
    LoginSerializer,
    RegisterSerializer,
    SessionUserSerializer,
    UserSerializer,
)
from apps.core.schema import ErrorSerializer


def _session_response(user: User, access: str, refresh: str) -> Response:
    response = Response({"access": access, "user": SessionUserSerializer(user).data})
    cookie = settings.REFRESH_COOKIE
    response.set_cookie(
        cookie["key"],
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=cookie["path"],
        httponly=cookie["httponly"],
        samesite=cookie["samesite"],
        secure=cookie["secure"],
    )
    return response


def _delete_refresh_cookie(response: Response) -> Response:
    cookie = settings.REFRESH_COOKIE
    response.delete_cookie(cookie["key"], path=cookie["path"], samesite=cookie["samesite"])
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="auth_register",
        request=RegisterSerializer,
        responses={201: UserSerializer, 400: OpenApiResponse(), 409: ErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        operation_id="auth_login",
        request=LoginSerializer,
        responses={200: AuthSessionSerializer, 401: ErrorSerializer, 429: OpenApiResponse()},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.authenticate_user(request=request, **serializer.validated_data)
        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)
        return _session_response(user, str(refresh.access_token), str(refresh))


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="auth_refresh",
        request=None,
        responses={200: AuthSessionSerializer, 401: ErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        token = request.COOKIES.get(settings.REFRESH_COOKIE["key"])
        serializer = TokenRefreshSerializer(data={"refresh": token or ""})
        try:
            serializer.is_valid(raise_exception=True)
        # Empty (ValidationError); expired, malformed, or its user is gone or inactive
        # (InvalidToken / AuthenticationFailed); blacklisted (a bare TokenError in simplejwt 5.5).
        except (ValidationError, AuthenticationFailed, TokenError):
            response = Response(
                {"code": "session_expired", "detail": "La sesión ha caducado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return _delete_refresh_cookie(response)

        # With rotation on, the old refresh token is now blacklisted and a new one issued.
        access = serializer.validated_data["access"]
        refresh = serializer.validated_data["refresh"]
        user = User.objects.get(pk=RefreshToken(refresh)["user_id"])
        return _session_response(user, access, refresh)


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="auth_logout", request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        token = request.COOKIES.get(settings.REFRESH_COOKIE["key"])
        if token:
            with suppress(TokenError):  # already invalid: nothing to revoke
                RefreshToken(token).blacklist()
        return _delete_refresh_cookie(Response(status=status.HTTP_204_NO_CONTENT))


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="auth_me", responses=SessionUserSerializer)
    def get(self, request: Request) -> Response:
        return Response(SessionUserSerializer(request.user).data)
