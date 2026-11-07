import hashlib
import math
from django.conf import settings
from .checkpoints import RouteGeometry
from .providers import ProviderError, get_json, tomtom_key
from .travel_time import timing_profile


def calculate_routes(origin, destination, departure, load_weight_lb):
    key = tomtom_key()
    start, end = origin['coordinates'], destination['coordinates']
    if start == end:
        raise ProviderError('Origin and destination resolve to the same location.', 'same_location', 422)
    locations = f'{start[1]},{start[0]}:{end[1]},{end[0]}'
    params = {
        'key': key, 'maxAlternatives': 2, 'alternativeType': 'anyRoute', 'travelMode': 'truck',
        'vehicleCommercial': 'true', 'vehicleWeight': math.ceil((load_weight_lb + settings.TRUCK_EMPTY_WEIGHT_LB)*0.45359237),
        'routeRepresentation': 'polyline', 'routeType': 'fastest', 'traffic': 'true',
        'extendedRouteRepresentation': ['distance', 'travelTime'],
        'departAt': departure.isoformat(), 'sectionType': 'travelMode', **settings.TRUCK_DIMENSIONS,
    }
    data = get_json(f'https://api.tomtom.com/routing/1/calculateRoute/{locations}/json', params, 'TomTom routing')
    routes, seen, warnings = [], set(), []
    try:
        raw_routes = data.get('routes', [])
        if not isinstance(raw_routes, list):
            raise TypeError()
        for raw in raw_routes:
            try:
                coordinates = []
                for leg in raw['legs']:
                    for point in leg['points']:
                        coordinate = [float(point['longitude']), float(point['latitude'])]
                        if not coordinates or coordinate != coordinates[-1]:
                            coordinates.append(coordinate)
                distance = float(raw['summary']['lengthInMeters'])
                duration = float(raw['summary']['travelTimeInSeconds'])
                RouteGeometry(coordinates, distance)
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError()
                signature = hashlib.sha256(str([[round(x, 5) for x in p] for p in coordinates]).encode()).hexdigest()
                if signature in seen:
                    warnings.append('A duplicate route alternative was omitted.')
                    continue
                seen.add(signature)
                truck_supported = not any(s.get('sectionType') == 'TRAVEL_MODE' and s.get('travelMode') != 'truck' for s in raw.get('sections', []))
                timing = timing_profile(raw.get('progress'), distance, duration)
                if timing is None:
                    warnings.append('Provider travel-time progress is unavailable or invalid; checkpoint ETAs use a uniform-speed estimate.')
                routes.append({'id': f'route-{len(routes)+1}', 'name': f'Route {len(routes)+1}', 'coordinates': coordinates,
                               'distance_meters': distance, 'duration_seconds': duration, 'truck_supported': truck_supported,
                               'timing': timing})
                if len(routes) == 3:
                    break
            except (KeyError, TypeError, ValueError, ProviderError):
                warnings.append('A route with invalid geometry, distance, or ETA was omitted.')
    except (AttributeError, TypeError):
        raise ProviderError('Routing returned an invalid response.') from None
    if not routes:
        raise ProviderError('No usable truck route was returned. Try more specific locations.', 'no_routes', 422)
    if len(routes) < 3:
        warnings.append(f'The provider returned {len(routes)} distinct route option(s); no additional routes were invented.')
    return routes, warnings
