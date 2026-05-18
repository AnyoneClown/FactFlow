"""Development settings for FactFlow."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://factflow:factflow@localhost:5432/factflow",
    )
}
