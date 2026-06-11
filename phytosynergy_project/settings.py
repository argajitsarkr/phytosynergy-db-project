import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SECURITY & PRODUCTION SETTINGS
# ==============================================================================

# DEBUG is False by default (fail closed). Set DEBUG=1 in the environment for
# local development only - never in production.
DEBUG = os.environ.get('DEBUG', '0') == '1'

# SECRET_KEY: a throwaway key is allowed ONLY when DEBUG is on. In production
# (DEBUG off) the process must refuse to start without a real key set in the
# environment, so a missing key can never silently fall back to a known value.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY environment variable must be set in production.'
        )


# --- ALLOWED_HOSTS AND CSRF LOGIC ---
# Defaults to localhost only (fail closed); the deployment must set ALLOWED_HOSTS
# explicitly. Never defaults to '*'.
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

# CSRF trusted origins - needed for Cloudflare Tunnel, Railway, or any reverse proxy
CSRF_TRUSTED_ORIGINS = []

csrf_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_env:
    CSRF_TRUSTED_ORIGINS.extend([o.strip() for o in csrf_env.split(',') if o.strip()])

# Get the production hostname from Railway's official environment variable.
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append('https://' + RAILWAY_PUBLIC_DOMAIN)


# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    'synergy_data',
    'bootstrap5',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'phytosynergy_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'synergy_data.context_processors.view_counter',
            ],
        },
    },
]

WSGI_APPLICATION = 'phytosynergy_project.wsgi.application'


# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

# settings.py
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=False)
    }
else:
    # Your old local database settings here for when you develop on your laptop
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'phytosynergy_db',
            'USER': 'postgres',
            'PASSWORD': 'YOUR_LOCAL_DB_PASSWORD', # Your password on your laptop
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# If the DATABASE_URL environment variable exists, it will override the default settings.
if 'DATABASE_URL' in os.environ:
    DATABASES['default'].update(dj_database_url.config(conn_max_age=600, ssl_require=False))


# ==============================================================================
# STANDARD DJANGO SETTINGS
# ==============================================================================

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# AUTHENTICATION SETTINGS
# ==============================================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'data_entry'
LOGOUT_REDIRECT_URL = 'home'


# ==============================================================================
# SECURITY HARDENING (production only)
# ==============================================================================
# These are only enforced when DEBUG is off so they never get in the way of
# local HTTP development. The app runs behind nginx + a TLS-terminating tunnel
# (ngrok / Cloudflare), so Django must trust the proxy's X-Forwarded-Proto
# header to know the original request was HTTPS.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Redirect any plain-HTTP request to HTTPS. Disable with SECURE_SSL_REDIRECT=0
    # if your proxy already guarantees HTTPS and you hit redirect loops.
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', '1') == '1'

    # Cookies only travel over HTTPS and are not readable from JavaScript.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    # Misc hardening headers.
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'

    # HSTS: enabled via SECURE_HSTS_SECONDS env var (set to 31536000 in
    # docker-compose.yml now that phytosynergydb.in is a dedicated domain).
    # To disable temporarily, set SECURE_HSTS_SECONDS=0 in the environment.
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
    if SECURE_HSTS_SECONDS:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = (
            os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', '1') == '1'
        )
        SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', '0') == '1'


# ==============================================================================
# LOGGING
# ==============================================================================
# Log to stdout/stderr so `docker compose logs web` captures everything. Without
# this, application errors in production are swallowed silently.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'synergy_data': {
            'handlers': ['console'],
            'level': os.environ.get('APP_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
