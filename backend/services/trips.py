from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import math
from uuid import uuid4
from django.core.cache import cache
from .checkpoints import RouteGeometry, METERS_PER_MILE, generate_checkpoints
from .geocoding import geocode
from .providers import ProviderError
from .recommendation import recommend
from .risk_engine import calculate_checkpoint_risk, calculate_route_risk, segment_risk
from .routing import calculate_routes
from .weather import coordinate_key, fetch_forecasts, weather_at

TRIP_TTL = 3600


def corridor_points(raw_routes):
    """Actual forecasts at centerline and +/-12-mile cross-corridor samples every 50 mi."""
    points = []
    seen = set()
    for route in raw_routes:
        geometry = RouteGeometry(route['coordinates'], route['distance_meters'])
        count = max(1, math.ceil(geometry.total / (50*METERS_PER_MILE)))
        for index in range(count+1):
            distance = geometry.total*index/count
            center = geometry.position(distance)
            before = geometry.position(max(0, distance-500))
            after = geometry.position(min(geometry.total, distance+500))
            dx = ((after[0]-before[0]+180) % 360-180)*math.cos(math.radians(center[1]))
            dy = after[1]-before[1]
            length = math.hypot(dx, dy) or 1
            for offset in (-12, 0, 12):
                lat = max(-89.9, min(89.9, center[1] + dx/length*offset/69))
                lon = (center[0] - dy/length*offset/(69*max(0.05, math.cos(math.radians(center[1]))))+180) % 360-180
                coordinate = [lon, lat]
                key = coordinate_key(coordinate)
                if key not in seen:
                    seen.add(key)
                    points.append({'id': f'corridor-{len(points)}', 'coordinates': coordinate, 'kind': 'corridor'})
    return points


def calculate_trip(inputs):
    with ThreadPoolExecutor(max_workers=2) as pool:
        origin_future = pool.submit(geocode, inputs['origin'])
        destination_future = pool.submit(geocode, inputs['destination'])
        origin, destination = origin_future.result(), destination_future.result()
    raw_routes, warnings = calculate_routes(origin, destination, inputs['departure_at'], inputs['load_weight_lb'])
    routes = []
    for raw in raw_routes:
        geometry = RouteGeometry(raw['coordinates'], raw['distance_meters'])
        checkpoints = generate_checkpoints(geometry, inputs['interval_miles'], raw['duration_seconds'], inputs['departure_at'], raw['id'], raw.get('timing'))
        routes.append({'id': raw['id'], 'name': raw['name'], 'geometry': {'type': 'LineString', 'coordinates': raw['coordinates']},
                       'distance_miles': raw['distance_meters']/METERS_PER_MILE, 'duration_seconds': raw['duration_seconds'],
                       'arrival_at': checkpoints[-1]['eta'], 'truck_supported': raw['truck_supported'], 'checkpoints': checkpoints})
    points = [{'id': cp['id'], 'coordinates': cp['coordinates'], 'kind': 'checkpoint'} for route in routes for cp in route['checkpoints']]
    points.extend(corridor_points(raw_routes))
    series, weather_warnings = fetch_forecasts([point['coordinates'] for point in points])
    warnings.extend(weather_warnings)
    for raw, route in zip(raw_routes, routes):
        for checkpoint in route['checkpoints']:
            checkpoint['weather'] = weather_at(series.get(coordinate_key(checkpoint['coordinates'])), datetime.fromisoformat(checkpoint['eta']))
            checkpoint['risk'] = calculate_checkpoint_risk(checkpoint['weather'], inputs['load_weight_lb'])
        route['summary'] = calculate_route_risk(route['checkpoints'], route['truck_supported'])
        geometry = RouteGeometry(raw['coordinates'], raw['distance_meters'])
        route['segments'] = [{'start_miles': left['distance_miles'], 'end_miles': right['distance_miles'],
                              'risk': segment_risk(left['risk'], right['risk']),
                              'geometry': {'type': 'LineString', 'coordinates': geometry.slice(left['distance_miles']*METERS_PER_MILE, right['distance_miles']*METERS_PER_MILE)}}
                             for left, right in zip(route['checkpoints'], route['checkpoints'][1:])]
    recommended, reason = recommend(routes)
    warnings.append('Sampled weather estimates; segment risk uses the more severe endpoint. Conditions between checkpoints can differ.')
    warnings.append('Truck routing uses configured empty weight plus cargo. Verify vehicle dimensions, road restrictions, and driving/rest limits; ETA excludes rest stops.')
    if any(not route['summary']['complete'] for route in routes):
        warnings.append('Weather coverage is incomplete. Affected routes cannot be recommended. Forecasts may be outside the available horizon.')
    if any(not route['truck_supported'] for route in routes):
        warnings.append('The provider returned a section without truck travel mode; affected routes are ineligible.')
    result = {'id': str(uuid4()), 'origin': origin, 'destination': destination, 'departure_at': inputs['departure_at'].isoformat(),
              'forecast_base_at': inputs['departure_at'].isoformat(), 'load_weight_lb': inputs['load_weight_lb'], 'interval_miles': inputs['interval_miles'],
              'routes': routes, 'recommended_route_id': recommended, 'recommendation_reason': reason,
              'warnings': list(dict.fromkeys(warnings)), 'providers': {'routing': 'TomTom truck', 'weather': 'Open-Meteo'}, 'expires_in_seconds': TRIP_TTL}
    # One process with threads in deployment: the process-local cache is intentional, not durable storage.
    cache.set(f'trip:{result["id"]}', {'result': result, 'points': points, 'series': series}, TRIP_TTL)
    return result


def get_trip(trip_id):
    trip = cache.get(f'trip:{trip_id}')
    if trip is None:
        raise ProviderError('This trip has expired or the server restarted. Calculate routes again.', 'trip_expired', 404)
    return trip


def forecast_for_trip(trip_id, hour):
    trip = get_trip(trip_id)
    result = trip['result']
    timestamp = datetime.fromisoformat(result['forecast_base_at']) + timedelta(hours=hour)
    points = []
    for point in trip['points']:
        weather = weather_at(trip['series'].get(coordinate_key(point['coordinates'])), timestamp)
        points.append({**point, 'weather': weather, 'risk': calculate_checkpoint_risk(weather, result['load_weight_lb'])})
    return {'hour': hour, 'timestamp': timestamp.isoformat(), 'points': points,
            'missing_count': sum(not p['risk']['complete'] for p in points), 'total_points': len(points)}
