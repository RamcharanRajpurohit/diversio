"""Deliberately minimal settings.

The exercise analyses an upload and renders a page. It never persists anything,
so there is no database, no auth, no sessions and no admin. Everything left
here is something a request actually needs.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Local exercise only; a real deployment would read this from the environment.
SECRET_KEY = "django-insecure-hris-import-preview-exercise"
DEBUG = True
# Empty is the startproject default: with DEBUG on, Django accepts localhost,
# 127.0.0.1 and [::1] automatically, and the test runner adds "testserver".
ALLOWED_HOSTS = []

INSTALLED_APPS = ["preview"]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {},
    }
]

# No models are defined, so no connection is ever opened.
DATABASES = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

# Reject oversized uploads at the request boundary, before any parsing work is
# scheduled. FILE_UPLOAD_MAX_MEMORY_SIZE is left at its 2.5 MB default, so a
# large HRIS export is streamed to a temp file rather than held in memory.
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
