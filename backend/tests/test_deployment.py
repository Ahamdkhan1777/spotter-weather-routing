from datetime import timedelta
from unittest.mock import patch

import fakeredis
import redis
from django.core.cache.backends.redis import RedisCache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from redis.exceptions import ConnectionError
from rest_framework.test import APIClient

from config.cache import cache_settings, deployment_hosts
from services.checkpoints import METERS_PER_MILE
from services.providers import ProviderError
from services.trips import calculate_trip, forecast_for_trip, get_trip
from services.weather import coordinate_key, normalize_forecast
from tests.test_weather import weather_fixture


class CacheConfigurationTests(SimpleTestCase):
    def test_local_default_is_unchanged(self):
        config = cache_settings({})['default']
        self.assertEqual(config['BACKEND'], 'django.core.cache.backends.locmem.LocMemCache')

    def test_vercel_requires_shared_tls_storage(self):
        for url in ['', 'redis://localhost:6379']:
            with self.subTest(url=url), self.assertRaises(ImproperlyConfigured):
                cache_settings({'VERCEL': '1', 'REDIS_URL': url})

    def test_invalid_url_errors_do_not_expose_credentials(self):
        for url in ['https://secret-token@cache.example', 'rediss://secret-token@host:bad', 'rediss://', 'file:///tmp/cache']:
            with self.subTest(url=url), self.assertRaises(ImproperlyConfigured) as error:
                cache_settings({'REDIS_URL': url})
            self.assertNotIn('secret-token', str(error.exception))

    def test_redis_and_deployment_namespaces(self):
        base = {'VERCEL': '1', 'REDIS_URL': 'rediss://default:synthetic-password@cache.example:6379',
                'VERCEL_ENV': 'production', 'VERCEL_URL': 'deployment-a.example'}
        a = cache_settings(base)['default']
        b = cache_settings({**base, 'VERCEL_URL': 'deployment-b.example'})['default']
        self.assertEqual(a['BACKEND'], 'django.core.cache.backends.redis.RedisCache')
        self.assertNotEqual(a['KEY_PREFIX'], b['KEY_PREFIX'])
        self.assertEqual(a['OPTIONS']['socket_timeout'], 5)
        self.assertEqual(a['OPTIONS']['socket_connect_timeout'], 3)

    def test_vercel_hosts_are_specific(self):
        hosts = deployment_hosts({'VERCEL_URL': 'preview.example', 'VERCEL_PROJECT_PRODUCTION_URL': 'app.example'})
        self.assertEqual(hosts, ['preview.example', 'app.example'])
        self.assertNotIn('*', hosts)


class SharedTripStorageTests(SimpleTestCase):
    def setUp(self):
        server = fakeredis.FakeServer()

        class FakePool:
            @classmethod
            def from_url(cls, url, **options):
                return redis.ConnectionPool(connection_class=fakeredis.FakeConnection, server=server, **options)

        params = cache_settings({'REDIS_URL': 'redis://localhost:6379/0'})['default']
        params['OPTIONS']['pool_class'] = FakePool
        self.first = RedisCache(params['LOCATION'], params)
        self.second = RedisCache(params['LOCATION'], params)

    def test_independent_cache_instances_share_trip_values_and_ttl(self):
        stored = {'result': {'id': 'shared', 'routes': []}, 'series': {'point': {'rows': [None, 3.5]}}}
        self.first.set('trip:shared', stored, 3600)
        self.assertEqual(self.second.get('trip:shared'), stored)
        ttl = self.second._cache.get_client().ttl(self.second.make_key('trip:shared'))
        self.assertTrue(0 < ttl <= 3600)
        self.first.close()
        self.assertEqual(self.second.get('trip:shared'), stored)

    def test_different_namespaces_do_not_share_trips(self):
        self.first.set('trip:shared', {'id': 'shared'}, 3600)
        self.second.key_prefix = 'another-deployment'
        self.assertIsNone(self.second.get('trip:shared'))

    @patch('services.trips.geocode')
    @patch('services.trips.calculate_routes')
    @patch('services.trips.fetch_forecasts')
    def test_calculation_and_slider_work_on_different_instances(self, weather, routing, geocoding):
        departure = timezone.now() + timedelta(hours=1)
        geocoding.side_effect = lambda query: {'label': query, 'coordinates': [-96, 32] if query == 'Dallas' else [-95.5, 32.4]}
        routing.return_value = ([{'id': 'route-1', 'name': 'Route 1', 'coordinates': [[-96, 32], [-95.5, 32.4]],
                                  'distance_meters': 30 * METERS_PER_MILE, 'duration_seconds': 3600,
                                  'truck_supported': True}], [])
        fixture = weather_fixture(start=int(departure.timestamp() // 3600 * 3600))
        fixture['hourly']['wind_speed_10m'][48:51] = [60, 60, 60]
        series = normalize_forecast(fixture)
        weather.side_effect = lambda coords: ({coordinate_key(point): series for point in coords}, [])
        with patch('services.trips.cache', self.first):
            trip = calculate_trip({'origin': 'Dallas', 'destination': 'Tyler', 'departure_at': departure,
                                   'load_weight_lb': 10000, 'interval_miles': 25})
        with patch('services.trips.cache', self.second):
            forecast = forecast_for_trip(trip['id'], 48)
            self.assertEqual(forecast['points'][0]['risk']['level'], 'No Travel')
            self.assertEqual(get_trip(trip['id'])['result']['recommended_route_id'], 'route-1')
            self.assertEqual(get_trip(trip['id'])['result']['routes'][0]['checkpoints'][0]['risk']['level'], 'Low')
            self.second.delete(f'trip:{trip["id"]}')
            with self.assertRaises(ProviderError) as error:
                get_trip(trip['id'])
            self.assertEqual(error.exception.code, 'trip_expired')


class StorageFailureTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    @patch('routing.views.forecast_for_trip', side_effect=ConnectionError('rediss://default:secret-token@cache.example'))
    def test_storage_outage_is_sanitized(self, forecast):
        response = APIClient().get('/api/trips/00000000-0000-0000-0000-000000000000/forecast/?hour=12')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'cache_unavailable')
        self.assertNotIn('secret-token', response.content.decode())

    @override_settings(DEBUG=False)
    @patch('rest_framework.throttling.AnonRateThrottle.allow_request', side_effect=ConnectionError('private-cache-token'))
    def test_throttle_cache_outage_is_also_sanitized(self, throttle):
        response = APIClient().get('/api/places/?q=Dallas')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private-cache-token', response.content.decode())
