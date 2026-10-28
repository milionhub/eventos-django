from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

HealthSerializer = inline_serializer(
    name="Health",
    fields={"api": serializers.BooleanField(), "database": serializers.BooleanField()},
)


class HealthView(APIView):
    """Liveness check that also verifies the database connection."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="health_retrieve",
        # 503 shares the body shape so clients can tell which component is down.
        responses={200: HealthSerializer, 503: HealthSerializer},
    )
    def get(self, request: Request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            database_ok = True
        except Exception:
            database_ok = False
        return Response({"api": True, "database": database_ok}, status=200 if database_ok else 503)
