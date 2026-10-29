from .base import *  # noqa: F403
from .base import env

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HTTPS only. A local demo over plain http (docker compose on localhost) turns both off
# through the environment instead of editing this file.
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# HSTS: browsers refuse plain http for this long once they have seen the header. Starts at
# one hour because a wrong value cannot be taken back from browsers that cached it; raise it
# (e.g. 31536000) once HTTPS is known to work. No preload: that needs control of the domain.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# The HSTS preload list is for domains we own; with no budget there is no domain of our own.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
