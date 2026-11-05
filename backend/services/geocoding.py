import hashlib
import math
from urllib.parse import quote
from django.core.cache import cache
from .providers import ProviderError, get_json, tomtom_key


def search_places(query, limit=5):
    key = tomtom_key()
    cache_key = 'geocode:' + hashlib.sha256(f'{query.lower()}:{limit}'.encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = get_json(f'https://api.tomtom.com/search/2/search/{quote(query, safe="")}.json', {
        'key': key, 'limit': limit, 'typeahead': 'false', 'idxSet': 'Geo,PAD,Addr,Str',
    }, 'TomTom geocoding')
    places = []
    try:
        for item in data.get('results', []):
            lat, lon = float(item['position']['lat']), float(item['position']['lon'])
            if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                continue
            address = item.get('address', {})
            label = address.get('freeformAddress') or item.get('poi', {}).get('name') or query
            places.append({'label': label, 'coordinates': [lon, lat]})
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ProviderError('Geocoding returned invalid location data.') from None
    cache.set(cache_key, places, 86400)
    return places


def geocode(query):
    places = search_places(query, 1)
    if not places:
        raise ProviderError(f'No location found for “{query}”. Try a city, state, or full address.', 'location_not_found', 422)
    return places[0]
