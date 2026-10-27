from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness check that also verifies the database connection."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="health_retrieve",
        responses=inline_serializer(
            name="Health",
            fields={"api": serializers.BooleanField(), "database": serializers.BooleanField()},
        ),
    )
    def get(self, request: Request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            database_ok = True
        except Exception:
            database_ok = False
        return Response({"api": True, "database": database_ok}, status=200 if database_ok else 503)
