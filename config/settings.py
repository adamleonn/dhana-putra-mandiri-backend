"""
Django settings for CV Dhana Putra Mandiri (Mini-ERP).
Enterprise-hardened distribution, inventory logistics, double-entry finance, and HR payroll.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

APP_ENV = os.getenv('APP_ENV', 'development').lower()
DEBUG = os.getenv('DEBUG', 'True' if APP_ENV != 'production' else 'False').lower() in ('true', '1', 't')
DEMO_MODE = os.getenv('DEMO_MODE', 'True' if APP_ENV != 'production' else 'False').lower() in ('true', '1', 't')

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if APP_ENV == 'production':
        raise ImproperlyConfigured("SECRET_KEY wajib diset pada environment production!")
    SECRET_KEY = 'django-insecure-wc!1lnmg&*he3kw=bi#v0v9w6gjkk7%1m8gngv^o!7yn!xp^w)'

# Production Safeguards
if APP_ENV == 'production':
    if DEBUG:
        raise ImproperlyConfigured("DEBUG dilarang aktif pada environment production!")
    if DEMO_MODE:
        raise ImproperlyConfigured("DEMO_MODE dilarang aktif pada environment production!")
    if os.getenv('DB_PASSWORD') in ('postgres', '', None):
        raise ImproperlyConfigured("DB_PASSWORD tidak boleh menggunakan password default pada production!")

_allowed_hosts_env = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(',') if host.strip()]

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    # Third-party packages
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',

    # Domain apps
    'core.apps.CoreConfig',
    'inventory.apps.InventoryConfig',
    'finance.apps.FinanceConfig',
    'hr.apps.HrConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration (PostgreSQL strictly required for select_for_update & ExclusionConstraints)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'dhana_putra_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60')),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'id'
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Jakarta')
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Configuration
_cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = False

# Django REST Framework Configuration
_default_renderers = ['rest_framework.renderers.JSONRenderer']
if DEBUG:
    _default_renderers.append('rest_framework.renderers.BrowsableAPIRenderer')

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'config.auth.OIDCAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': _default_renderers,
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('THROTTLE_ANON', '100/min'),
        'user': os.getenv('THROTTLE_USER', '1000/min'),
    }
}

# Spectacular OpenAPI Documentation Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'CV Dhana Putra Mandiri - Mini ERP Backend API',
    'DESCRIPTION': 'Production API for Cooking Oil Distribution, Logistics, Accounting & HR Payroll',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Production Security Headers
if APP_ENV == 'production':
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    _csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', 'https://localhost')
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(',') if origin.strip()]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
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
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Authlib / OpenID Connect
AUTHLIB_OAUTH_CLIENTS = {
    'oidc_provider': {
        'client_id': os.getenv('OIDC_CLIENT_ID', ''),
        'client_secret': os.getenv('OIDC_CLIENT_SECRET', ''),
        'server_metadata_url': os.getenv('OIDC_SERVER_METADATA_URL', ''),
        'client_kwargs': {
            'scope': 'openid email profile',
        },
    }
}
OIDC_API_AUDIENCE = os.getenv('OIDC_API_AUDIENCE', 'dhana-putra-api')
