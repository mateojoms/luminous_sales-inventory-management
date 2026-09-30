from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def get_env(name, django_name=None, default=None):
    """Read the documented setting name, keeping support for earlier DJANGO_* names."""
    if django_name and os.environ.get(django_name) is not None:
        return os.environ[django_name]
    return os.environ.get(name, default)


DEBUG_VALUE = get_env("DEBUG", "DJANGO_DEBUG", "0" if os.environ.get("VERCEL") else "1")
DEBUG = DEBUG_VALUE.strip().lower() in {"1", "true", "yes", "on"}
SECRET_KEY = get_env("SECRET_KEY", "DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set SECRET_KEY (or DJANGO_SECRET_KEY) when DEBUG is disabled.")
    SECRET_KEY = "dev-only-change-me-before-deployment"

vercel_url = os.environ.get("VERCEL_URL", "").strip()
allowed_hosts_value = get_env("ALLOWED_HOSTS", "DJANGO_ALLOWED_HOSTS")
if allowed_hosts_value is None:
    allowed_hosts_value = "127.0.0.1,localhost" if DEBUG else vercel_url
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_value.split(",") if host.strip()]
if vercel_url and vercel_url not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(vercel_url)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS (or DJANGO_ALLOWED_HOSTS) for production.")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "manager",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "stamp_manager.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "manager.context_processors.navigation",
    ]},
}]
WSGI_APPLICATION = "stamp_manager.wsgi.application"
ASGI_APPLICATION = "stamp_manager.asgi.application"
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    database_config = dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG)
    if not DEBUG and database_config["ENGINE"] != "django.db.backends.postgresql":
        raise ImproperlyConfigured("Production DATABASE_URL must use PostgreSQL.")
    DATABASES = {"default": database_config}
elif DEBUG:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    raise ImproperlyConfigured("Set DATABASE_URL to a persistent PostgreSQL database when DEBUG is disabled.")
AUTH_USER_MODEL = "manager.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

csrf_origins_value = get_env("CSRF_TRUSTED_ORIGINS", "DJANGO_CSRF_TRUSTED_ORIGINS")
if csrf_origins_value is None:
    csrf_origins_value = (
        "http://localhost:8000,http://127.0.0.1:8000"
        if DEBUG
        else f"https://{vercel_url}" if vercel_url else ""
    )
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_value.split(",") if origin.strip()]
if vercel_url:
    vercel_origin = f"https://{vercel_url}"
    if vercel_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(vercel_origin)
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("Set CSRF_TRUSTED_ORIGINS for production, including your HTTPS domain.")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
