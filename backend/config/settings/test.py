from .base import *  # noqa: F403

DEBUG = False

# Hashing passwords with the default algorithm is deliberately slow; tests don't need that.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
