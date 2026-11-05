from bisect import bisect_right
from datetime import timedelta
import math
from .providers import ProviderError

METERS_PER_MILE = 1609.344
EARTH_METERS = 6371008.8


def haversine(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2 * EARTH_METERS * math.asin(min(1, math.sqrt(h)))


def interpolate(a, b, fraction):
    """Spherical interpolation also handles road geometry crossing the antimeridian."""
    if fraction <= 0:
        return list(a)
    if fraction >= 1:
        return list(b)
    vectors = []
    for lon, lat in (a, b):
        lon, lat = math.radians(lon), math.radians(lat)
        vectors.append((math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)))
    angle = haversine(a, b) / EARTH_METERS
    if angle < 1e-12:
        return list(a)
    weights = [math.sin((1-fraction)*angle)/math.sin(angle), math.sin(fraction*angle)/math.sin(angle)]
    x, y, z = [sum(weights[i]*vectors[i][j] for i in range(2)) for j in range(3)]
    return [math.degrees(math.atan2(y, x)), math.degrees(math.atan2(z, math.hypot(x, y)))]


class RouteGeometry:
    def __init__(self, coordinates, distance_meters):
        if len(coordinates) < 2 or not math.isfinite(distance_meters) or distance_meters <= 0:
            raise ProviderError('Route is missing usable geometry or distance.')
        for point in coordinates:
            if len(point) != 2 or not all(math.isfinite(x) for x in point) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                raise ProviderError('Route contains invalid coordinates.')
        self.coordinates = coordinates
        self.cumulative = [0.0]
        for a, b in zip(coordinates, coordinates[1:]):
            self.cumulative.append(self.cumulative[-1] + haversine(a, b))
        if self.cumulative[-1] <= 0:
            raise ProviderError('Route geometry has zero length.')
        # Calibrate geometry arc lengths to the provider's road-distance summary.
        scale = distance_meters / self.cumulative[-1]
        self.cumulative = [d*scale for d in self.cumulative]
        self.total = distance_meters

    def position(self, distance):
        if distance >= self.total:
            return list(self.coordinates[-1])
        index = min(bisect_right(self.cumulative, max(0, distance))-1, len(self.coordinates)-2)
        width = self.cumulative[index+1] - self.cumulative[index]
        return interpolate(self.coordinates[index], self.coordinates[index+1], (distance-self.cumulative[index])/width if width else 0)

    def slice(self, start, end):
        left = bisect_right(self.cumulative, start)
        right = bisect_right(self.cumulative, end)
        return [self.position(start), *self.coordinates[left:right], self.position(end)]


def generate_checkpoints(geometry, interval_miles, duration_seconds, departure, route_id):
    if interval_miles not in (10, 25, 50):
        raise ValueError('Checkpoint interval must be 10, 25, or 50 miles.')
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ProviderError('Route is missing a usable travel duration.')
    step = interval_miles * METERS_PER_MILE
    count = int(math.floor(geometry.total / step))
    if count > 1200:
        raise ProviderError('This route exceeds the sampling limit. Choose a larger interval.', 'sampling_limit', 422)
    distances = [i*step for i in range(count+1)]
    if geometry.total - distances[-1] > 0.01:
        distances.append(geometry.total)
    else:
        distances[-1] = geometry.total
    return [{
        'id': f'{route_id}-cp-{index}', 'coordinates': geometry.position(distance),
        'distance_miles': distance / METERS_PER_MILE,
        'eta': (departure + timedelta(seconds=duration_seconds*distance/geometry.total)).isoformat(),
    } for index, distance in enumerate(distances)]
