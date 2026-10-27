from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Business rule violation raised by services.

    Subclasses define a stable machine-readable `code` (used by the frontend)
    and the HTTP status the API should answer with.
    """

    code = "domain_error"
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "La operación no está permitida."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


def exception_handler(exc, context):
    """DRF exception handler that also renders `DomainError` as `{code, detail}`."""
    if isinstance(exc, DomainError):
        return Response({"code": exc.code, "detail": exc.detail}, status=exc.status_code)
    return drf_exception_handler(exc, context)
