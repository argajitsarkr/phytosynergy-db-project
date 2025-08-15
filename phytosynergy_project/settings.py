import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SECURITY & PRODUCTION SETTINGS
# ==============================================================================

SECRET_KEY = os.environ.get(
    'SECRET_KEY', 
    'django-insecure-fallback-key-for-local-development-only'
)

# DEBUG is False in production, but True if we're running locally.
DEBUG = os.environ.get('DJANGO_DEBUG', '') == 'True'


# --- CORRECTED ALLOWED_HOSTS AND CSRF LOGIC ---
ALLOWED_HOSTS = [
    '127.0.0.1', # For local development
]

# Get the production hostname from Railway's official environment variable.
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    # This also tells Django to trust requests from your production site for secure forms.
    CSRF_TRUSTED_ORIGINS = ['https://' + RAILWAY_PUBLIC_DOMAIN]


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
            ],
        },
    },
]

WSGI_APPLICATION = 'phytosynergy_project.wsgi.application'


# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'phytosynergy_db',
        'USER': 'postgres',
        'PASSWORD': 'cU7qPwzFwgT*',
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
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"