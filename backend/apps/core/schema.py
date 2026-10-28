from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

# OpenAPI shape of a DomainError response (see apps.core.exceptions).
ErrorSerializer = inline_serializer(
    name="Error", fields={"code": serializers.CharField(), "detail": serializers.CharField()}
)
