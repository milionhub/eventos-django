from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

API_PREFIX = "/api/v1/"
# The API only returns data (JSON, the ticket's SVG, the CSV): opened directly in a browser,
# none of it may load or run anything, nor be framed by another site.
API_CONTENT_SECURITY_POLICY = "default-src 'none'; frame-ancestors 'none'"


class ApiContentSecurityPolicyMiddleware:
    """Strict CSP for the API. The Swagger docs and the admin load scripts, so they are left out;
    the Angular app gets its own policy from the web server that serves it."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.path.startswith(API_PREFIX):
            response.setdefault("Content-Security-Policy", API_CONTENT_SECURITY_POLICY)
        return response
