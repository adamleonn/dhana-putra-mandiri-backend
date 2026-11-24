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


def env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, 'True' if default else 'False').strip().lower() in ('true', '1', 't', 'yes')


def env_list(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if APP_ENV == 'production':
        raise ImproperlyConfigured("SECRET_KEY wajib diset pada environment production!")
    SECRET_KEY = 'django-insecure-wc!1lnmg&*he3kw=bi#v0v9w6gjkk7%1m8gngv^o!7yn!xp^w)'

# Production Safeguards
if APP_ENV == 'production':
    if DEBUG:
        raise ImproperlyConfigured("DEBUG dilarang aktif pada environment production!")
    if os.getenv('DB_PASSWORD') in ('postgres', '', None):
        raise ImproperlyConfigured("DB_PASSWORD tidak boleh menggunakan password default pada production!")

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

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
# Browser memanggil API melalui BFF Next.js (server-to-server), sehingga CORS
# hanya membuka origin frontend dan TIDAK mengizinkan kredensial/cookie.
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')
CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = ['accept', 'authorization', 'content-type', 'x-request-id']

# CSRF & Cookie (dipakai Django Admin; API memakai Bearer token tanpa cookie)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:8001')
_cookie_secure_default = APP_ENV == 'production'
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', _cookie_secure_default)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', _cookie_secure_default)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')

# Django REST Framework Configuration
_default_renderers = ['rest_framework.renderers.JSONRenderer']
if DEBUG:
    _default_renderers.append('rest_framework.renderers.BrowsableAPIRenderer')

REST_FRAMEWORK = {
    # Deny-by-default: setiap view wajib mendeklarasikan `role_access`.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'core.permissions.RoleBasedAccess',
    ],
    # Hanya OAuth 2.0 Bearer access token (JWT) dari IdP OIDC.
    # Token demo `demo-*` dan SessionAuthentication tidak lagi diterima API.
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'config.auth.OIDCAuthentication',
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
        'ai_summary': os.getenv('THROTTLE_AI_SUMMARY', '10/min'),
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
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_CONTENT_TYPE_NOSNIFF = True
    if not (SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE):
        raise ImproperlyConfigured("Cookie Secure wajib aktif pada environment production!")
    if any(o.startswith('http://') for o in CORS_ALLOWED_ORIGINS + CSRF_TRUSTED_ORIGINS):
        raise ImproperlyConfigured("CORS/CSRF origin production wajib HTTPS!")

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

# ---------------------------------------------------------------------------
# OAuth 2.0 / OpenID Connect (Resource Server)
# ---------------------------------------------------------------------------
# Issuer IdP, mis. Keycloak lokal: http://localhost:8080/realms/dhana-putra
OIDC_ISSUER = os.getenv('OIDC_ISSUER', '').rstrip('/')
# Opsional: default `<issuer>/.well-known/openid-configuration`
OIDC_DISCOVERY_URL = os.getenv('OIDC_DISCOVERY_URL', '')
# Opsional: override jwks_uri dari discovery
OIDC_JWKS_URL = os.getenv('OIDC_JWKS_URL', '')
# Audience yang wajib ada di klaim `aud` access token
OIDC_API_AUDIENCE = os.getenv('OIDC_API_AUDIENCE', 'dhana-putra-api')
OIDC_ALLOWED_ALGORITHMS = env_list('OIDC_ALLOWED_ALGORITHMS', 'RS256')
# Allowlist client (`azp`) yang boleh memanggil API; kosong = tidak dicek
OIDC_ALLOWED_CLIENT_IDS = env_list('OIDC_ALLOWED_CLIENT_IDS', '')
# Path klaim role (dot-notation), dipisah koma
OIDC_ROLE_CLAIM_PATHS = env_list('OIDC_ROLE_CLAIM_PATHS', f'resource_access.{OIDC_API_AUDIENCE}.roles')
# Pemetaan role IdP -> peran aplikasi, format "idp_role:app_role,..."
OIDC_ROLE_MAPPING = dict(
    pair.split(':', 1) for pair in env_list(
        'OIDC_ROLE_MAPPING', 'direktur:direktur,admin:admin,gudang:gudang,stakeholder:stakeholder'
    ) if ':' in pair
)
OIDC_LEEWAY_SECONDS = int(os.getenv('OIDC_LEEWAY_SECONDS', '30'))
OIDC_JWKS_CACHE_SECONDS = int(os.getenv('OIDC_JWKS_CACHE_SECONDS', '300'))
OIDC_HTTP_TIMEOUT_SECONDS = float(os.getenv('OIDC_HTTP_TIMEOUT_SECONDS', '5'))
# Migrasi pengguna lama: tautkan login OIDC pertama ke user lokal ber-username sama
OIDC_LINK_EXISTING_BY_USERNAME = env_bool('OIDC_LINK_EXISTING_BY_USERNAME', True)
OIDC_AUTO_CREATE_USERS = env_bool('OIDC_AUTO_CREATE_USERS', True)

if APP_ENV == 'production':
    if not OIDC_ISSUER.startswith('https://'):
        raise ImproperlyConfigured("OIDC_ISSUER wajib diset dan memakai HTTPS pada production!")
    if not OIDC_ALLOWED_CLIENT_IDS:
        raise ImproperlyConfigured("OIDC_ALLOWED_CLIENT_IDS wajib diset pada production!")

# -----------------------------------------------------------------------------
# Asisten ringkasan laporan (Small Language Model, API kompatibel OpenAI)
# Default: Ollama lokal (http://localhost:11434/v1) tanpa API key.
# API key HANYA dari environment/.env, jangan ditulis di kode.
# -----------------------------------------------------------------------------
AI_SUMMARY_ENABLED = env_bool('AI_SUMMARY_ENABLED', True)
AI_SUMMARY_BASE_URL = os.getenv('AI_SUMMARY_BASE_URL', 'http://localhost:11434/v1')
AI_SUMMARY_MODEL = os.getenv('AI_SUMMARY_MODEL', 'qwen2.5:1.5b')
AI_SUMMARY_API_KEY = os.getenv('AI_SUMMARY_API_KEY', '')
AI_SUMMARY_TIMEOUT_SECONDS = int(os.getenv('AI_SUMMARY_TIMEOUT_SECONDS', '120'))
AI_SUMMARY_MAX_TOKENS = int(os.getenv('AI_SUMMARY_MAX_TOKENS', '500'))
