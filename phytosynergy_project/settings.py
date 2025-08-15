import os
import dj_database_url
from pathlib import Path

# --- START OF DIAGNOSTIC BLOCK ---
# We will force the application to print its environment variables on startup.
# ==============================================================================
print("--- SETTINGS.PY FILE IS BEING LOADED ---")
db_url = os.environ.get('DATABASE_URL')
if db_url:
    print(f"SUCCESS: DATABASE_URL variable was found.")
else:
    print(f"CRITICAL FAILURE: The DATABASE_URL environment variable was NOT FOUND (is None).")

print(f"DJANGO_SETTINGS_MODULE is: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
print("--- END OF DIAGNOSTIC BLOCK ---")
# ==============================================================================


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SECURITY & PRODUCTION SETTINGS
# This section should come first.
# ==============================================================================

# Get the secret key from an environment variable for security.
SECRET_KEY = os.environ.get(
    'SECRET_KEY', 
    'django-insecure-fallback-key-for-local-development-only'
)

# DEBUG is False in production, but True if we're running locally.
# DEBUG will be True only if an environment variable named DJANGO_DEBUG is set to 'True'
DEBUG = os.environ.get('DJANGO_DEBUG', '') == 'True'

# Define the allowed hosts.
ALLOWED_HOSTS = [
    '127.0.0.1', # For local development
]

# Get the production hostname from Railway's official environment variable.
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

# CSRF and Trusted Origins for Production
# This tells Django to trust requests from your production site for secure forms.
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS = ['https://' + RAILWAY_PUBLIC_DOMAIN]

# ==============================================================================
# APPLICATION DEFINITION (RESTORED)
# This is the core Django configuration that was missing.
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
# This is the smart logic that switches between local and production.
# ==============================================================================

if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=False)
    }
else:
   DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'phytosynergy_db',
        'USER': 'postgres',
        'PASSWORD': 'cU7qPwzFwgT*', # <-- IMPORTANT: Put your local password here
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ==============================================================================
# PASSWORD VALIDATION, INTERNATIONALIZATION, STATIC FILES (Standard Stuff)
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

# CSRF and Trusted Origins for Production
if RAILWAY_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = ['https://' + RAILWAY_HOSTNAME]