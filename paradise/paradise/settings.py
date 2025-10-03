import os
from pathlib import Path

# --------------------------------------------------
# Base Directory
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------
# Security
# --------------------------------------------------
SECRET_KEY = 'django-insecure-=a1lapk3u+m&6l65pzi7k4od(rzg+tq4-5%#&uf4_yd6)hx+mg'

DEBUG = True  # ⚠️ Turn OFF in production (set False)
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",   # required for Django Test Client / manage.py shell Client()
]


# --------------------------------------------------
# Installed Apps
# --------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "booking",  # our app
]


# --------------------------------------------------
# Middleware
# --------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# --------------------------------------------------
# URL + WSGI
# --------------------------------------------------
ROOT_URLCONF = "paradise.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # ✅ Project-level templates
        "APP_DIRS": True,  # ✅ Look inside app/templates/
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "paradise.wsgi.application"


# --------------------------------------------------
# Database
# --------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --------------------------------------------------
# Authentication
# --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --------------------------------------------------
# Internationalization
# --------------------------------------------------
LANGUAGE_CODE = "en-us"

LANGUAGES = [
    ("en", "English"),
    ("bn", "Bengali"),
]

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / "locale",
]




# --------------------------------------------------
# Static & Media
# --------------------------------------------------
# For serving CSS, JS, images
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]  # for development
STATIC_ROOT = BASE_DIR / "staticfiles"    # for collectstatic in production

# For room images and user uploads
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# --------------------------------------------------
# Default primary key field type
# --------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# PayPal Settings ================================================================

PAYPAL_CLIENT_ID = "AXcoTkzjuLBB9DiaFF5H5-4OXtdoPHiZ2LhdWq0PPqt9_ZVJHhaFpIQY9rCwpeKMNU1af8op8TVfWnxV"
PAYPAL_CLIENT_SECRET = "ELRkcoi05qFqse1K1PCkM3bEphVH6WQx7gy8d6rLie8TctUhzamD4CKCMJPlLJNl9mOxdgkApX_lMFCm"
PAYPAL_MODE = "sandbox"  # "live" later


# =============================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "nuhad7july02@gmail.com"
EMAIL_HOST_PASSWORD = "rkypyfyuxuqoskzu"  # ⚠️ Use app password, not plain password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ========================================================================