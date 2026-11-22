"""Disposable local settings for an authenticated OWASP ZAP run only."""
import os
from .base import *

DEBUG = False
SECRET_KEY = "local-dast-only-key-not-for-deployment"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = []
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DAST_DB_PATH", str(BASE_DIR / "dast.sqlite3")),
    }
}
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
TRAINING_MODE = False
AXES_FAILURE_LIMIT = 10
