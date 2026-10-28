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
