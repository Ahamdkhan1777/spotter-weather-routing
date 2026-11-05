import requests
from django.conf import settings


class ProviderError(Exception):
    def __init__(self, message, code='provider_error', status=502):
        super().__init__(message)
        self.code = code
        self.status = status


def get_json(url, params, provider):
    """Never surface a requests exception: its URL can contain a private API key."""
    try:
        response = requests.get(url, params=params, timeout=(5, settings.PROVIDER_TIMEOUT_SECONDS))
        if response.status_code == 429:
            raise ProviderError(f'{provider} rate limit reached. Please retry later.', 'provider_rate_limit', 429)
        if response.status_code in (401, 403):
            raise ProviderError(f'{provider} credentials are missing, invalid, or not authorized.', 'provider_credentials', 503)
        if response.status_code >= 400:
            raise ProviderError(f'{provider} could not fulfill this request. Check locations and departure, then retry.')
        data = response.json()
        if not isinstance(data, (dict, list)):
            raise ValueError('Invalid response')
        return data
    except requests.Timeout:
        raise ProviderError(f'{provider} timed out. Please retry.', 'provider_timeout', 504) from None
    except (requests.RequestException, ValueError):
        raise ProviderError(f'{provider} is unavailable or returned an invalid response. Please retry.') from None


def tomtom_key():
    if not settings.TOMTOM_API_KEY:
        raise ProviderError('Routing is not configured. Add TOMTOM_API_KEY to backend/.env and restart the backend.', 'missing_api_key', 503)
    return settings.TOMTOM_API_KEY
