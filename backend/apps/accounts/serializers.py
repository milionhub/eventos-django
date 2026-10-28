from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import User
from apps.organizations.models import Membership


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class MembershipSummarySerializer(serializers.ModelSerializer):
    organization_slug = serializers.SlugField(source="organization.slug")
    organization_name = serializers.CharField(source="organization.name")

    class Meta:
        model = Membership
        fields = ["organization_slug", "organization_name", "role"]
        read_only_fields = fields


class SessionUserSerializer(UserSerializer):
    """The signed-in user plus their roles, so the frontend can adapt menus and guards.

    Only UX: every permission is checked again by the backend.
    """

    memberships = MembershipSummarySerializer(many=True, read_only=True)

    class Meta(UserSerializer.Meta):
        fields = [*UserSerializer.Meta.fields, "memberships"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        # Django's validators need a user to reject passwords similar to the name or email.
        candidate = User(
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class AuthSessionSerializer(serializers.Serializer):
    """Response of login and refresh: the access token plus who it belongs to."""

    access = serializers.CharField()
    user = SessionUserSerializer()
