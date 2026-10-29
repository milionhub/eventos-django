import json

from rest_framework.renderers import BaseRenderer


class SVGRenderer(BaseRenderer):
    """Lets a view answer `Accept: image/svg+xml`; DRF would otherwise reply 406.

    The view passes the SVG bytes through. Errors (404...) still carry a JSON body.
    """

    media_type = "image/svg+xml"
    format = "svg"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None) -> bytes:
        if isinstance(data, bytes):
            return data
        return json.dumps(data).encode()


class CSVRenderer(BaseRenderer):
    """Lets a view answer `Accept: text/csv`. The view streams the CSV itself; this only
    renders errors (404...), as JSON."""

    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None) -> bytes:
        return json.dumps(data).encode()
