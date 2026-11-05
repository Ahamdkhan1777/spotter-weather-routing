import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'development-only-spotter-key')
if not DEBUG and SECRET_KEY in ('development-only-spotter-key', 'local-development-change-before-deployment'):
    raise ValueError('Set a unique SECRET_KEY before running in production.')
ALLOWED_HOSTS = [x.strip() for x in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if x.strip()]
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.staticfiles', 'rest_framework', 'corsheaders', 'routing']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware', 'django.middleware.common.CommonMiddleware']
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
USE_TZ = True
TIME_ZONE = 'UTC'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = [x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'spotter', 'OPTIONS': {'MAX_ENTRIES': 2500}}}
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '120/hour'},
}
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_ROOT = BASE_DIR.parent / 'frontend' / 'dist'
WHITENOISE_MAX_AGE = 86400
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', str(not DEBUG)).lower() == 'true'
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY', '')
TRUCK_EMPTY_WEIGHT_LB = float(os.getenv('TRUCK_EMPTY_WEIGHT_LB', '18000'))
TRUCK_DIMENSIONS = {key: float(os.environ[env]) for key, env in [('vehicleHeight', 'TRUCK_HEIGHT_M'), ('vehicleWidth', 'TRUCK_WIDTH_M'), ('vehicleLength', 'TRUCK_LENGTH_M')] if os.getenv(env)}
PROVIDER_TIMEOUT_SECONDS = float(os.getenv('PROVIDER_TIMEOUT_SECONDS', '15'))
WEATHER_API_URL = os.getenv('WEATHER_API_URL', 'https://api.open-meteo.com/v1/forecast')
OPEN_METEO_API_KEY = os.getenv('OPEN_METEO_API_KEY', '')
MAX_WEATHER_LOCATIONS = int(os.getenv('MAX_WEATHER_LOCATIONS', '450'))
