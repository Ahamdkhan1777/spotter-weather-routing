"""Use shared Redis on Vercel and preserve the existing local-memory default."""
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


def cache_settings(environ):
    url = environ.get('REDIS_URL', '').strip()
    on_vercel = environ.get('VERCEL') == '1'
    if not url:
        if on_vercel:
            raise ImproperlyConfigured('Set REDIS_URL before deploying to Vercel; trip forecasts require shared storage.')
        return {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                            'LOCATION': 'spotter', 'OPTIONS': {'MAX_ENTRIES': 2500}}}
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme in ('redis', 'rediss') and parsed.hostname and (parsed.port is None or 0 < parsed.port <= 65535)
    except ValueError:
        valid = False
    if not valid:
        raise ImproperlyConfigured('REDIS_URL must be a Redis TCP connection URL (redis:// or rediss://), not an HTTPS REST URL.')
    if on_vercel and parsed.scheme != 'rediss':
        raise ImproperlyConfigured('Use a TLS rediss:// connection for REDIS_URL on Vercel.')

    from redis.backoff import NoBackoff
    from redis.retry import Retry

    # Instances of a deployment share keys; deployments/environments stay isolated.
    scope = ':'.join([environ.get('CACHE_KEY_PREFIX', 'spotter'), environ.get('VERCEL_ENV', 'local'),
                      environ.get('VERCEL_URL', 'local')])
    return {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': url,
                        'KEY_PREFIX': scope, 'OPTIONS': {'socket_connect_timeout': 3, 'socket_timeout': 5,
                                                       'retry': Retry(NoBackoff(), 0)}}}


def deployment_hosts(environ):
    return [environ[name] for name in ('VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL')
            if environ.get(name)]
