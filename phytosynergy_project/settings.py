import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SECURITY & PRODUCTION SETTINGS
# ==============================================================================

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'a-default-secret-key-for-development')
# In production, ensure DJANGO_SECRET_KEY is set in the environment variables.

# DEBUG is False in production, but True if we're running locally.
DEBUG = os.environ.get('DEBUG', '1') == '1' # Defaults to True for development


# ALLOWED_HOSTS: comma-separated list set in the .env file on the server.
# e.g.  ALLOWED_HOSTS=192.168.1.100,phytosynergydb.yourdomain.com
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# CSRF trusted origins: needed when the site is accessed over HTTPS.
# e.g.  CSRF_TRUSTED_ORIGINS=https://phytosynergydb.yourdomain.com
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]


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