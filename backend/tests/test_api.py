from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch, Mock
import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from services.checkpoints import METERS_PER_MILE
from services.providers import ProviderError, get_json
from services.routing import calculate_routes
from routing.serializers import TripSerializer
from services.weather import coordinate_key, normalize_forecast
from tests.test_weather import weather_fixture


def route_fixture():
    return {'routes': [{'summary': {'lengthInMeters': 30*METERS_PER_MILE, 'travelTimeInSeconds': 3600},
                        'legs': [{'points': [{'longitude': -96, 'latitude': 32}, {'longitude': -95.8, 'latitude': 32.2}, {'longitude': -95.5, 'latitude': 32.4}]}],
                        'sections': [{'sectionType': 'TRAVEL_MODE', 'travelMode': 'truck'}]}]}


class APITests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.departure = timezone.now()+timedelta(hours=1)
        self.payload = {'origin': 'Dallas, TX', 'destination': 'Tyler, TX', 'departure_at': self.departure.isoformat(), 'load_weight_lb': 35000, 'interval_miles': 25}

    def test_health(self):
        self.assertEqual(self.client.get('/api/health/').status_code, 200)

    @override_settings(TOMTOM_API_KEY='')
    def test_missing_key(self):
        response = self.client.post('/api/routes/calculate/', self.payload, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'missing_api_key')

    def test_invalid_inputs(self):
        for changes in [{'load_weight_lb': -1}, {'load_weight_lb': 'NaN'}, {'load_weight_lb': 0}, {'origin': ''}, {'destination': 'Dallas, TX'}, {'interval_miles': 20}, {'departure_at': '2026-11-05T10:00:00'}, {'departure_at': (timezone.now()-timedelta(days=1)).isoformat()}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post('/api/routes/calculate/', {**self.payload, **changes}, format='json').status_code, 400)

    @patch('services.trips.geocode')
    @patch('services.routing.get_json', return_value=route_fixture())
    @patch('services.weather.get_json')
    @override_settings(TOMTOM_API_KEY='test-secret')
    def test_end_to_end_calculation_and_slider_are_independent(self, weather, routing, geocoding):
        geocoding.side_effect = lambda query: {'label': query, 'coordinates': [-96, 32] if 'Dallas' in query else [-95.5, 32.4]}
        start = int(self.departure.timestamp()//3600*3600)
        fixture = weather_fixture(start=start)
        fixture['hourly']['wind_speed_10m'][48:51] = [60, 60, 60]
        def weather_response(url, params, provider):
            count = len(params['latitude'].split(','))
            return [fixture for _ in range(count)] if count > 1 else fixture
        weather.side_effect = weather_response
        response = self.client.post('/api/routes/calculate/', self.payload, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json()
        self.assertEqual(len(result['routes']), 1)
        self.assertEqual(result['recommended_route_id'], 'route-1')
        self.assertEqual(len(result['routes'][0]['checkpoints']), 3)
        self.assertAlmostEqual(result['routes'][0]['summary']['risk_miles']['Low'], 30)
        self.assertIn('1 distinct', ' '.join(result['warnings']))
        forecast = self.client.get(f'/api/trips/{result["id"]}/forecast/?hour=48')
        self.assertEqual(forecast.status_code, 200)
        self.assertEqual(forecast.json()['points'][0]['risk']['level'], 'No Travel')
        detail = self.client.get(f'/api/trips/{result["id"]}/').json()
        self.assertEqual(detail['recommended_route_id'], 'route-1')
        self.assertEqual(detail['routes'][0]['checkpoints'][0]['risk']['level'], 'Low')
        self.assertEqual(weather.call_count, 1)

    @patch('services.trips.geocode', side_effect=ProviderError('Timed out', 'provider_timeout', 504))
    def test_provider_timeout(self, get):
        response = self.client.post('/api/routes/calculate/', self.payload, format='json')
        self.assertEqual(response.status_code, 504)

    @patch('services.routing.get_json', return_value={'routes': []})
    @override_settings(TOMTOM_API_KEY='test')
    def test_no_routes(self, get):
        with self.assertRaises(ProviderError) as error:
            calculate_routes({'coordinates': [0, 0]}, {'coordinates': [1, 1]}, self.departure, 100)
        self.assertEqual(error.exception.code, 'no_routes')

    @patch('services.routing.get_json')
    @override_settings(TOMTOM_API_KEY='test')
    def test_duplicates_removed_and_truck_weight_converted(self, get):
        fixture = route_fixture()
        fixture['routes'] *= 3
        get.return_value = fixture
        routes, warnings = calculate_routes({'coordinates': [0, 0]}, {'coordinates': [1, 1]}, self.departure, 30000)
        self.assertEqual(len(routes), 1)
        self.assertTrue(any('duplicate' in warning for warning in warnings))
        self.assertEqual(get.call_args.args[1]['maxAlternatives'], 2)
        self.assertEqual(get.call_args.args[1]['travelMode'], 'truck')
        self.assertEqual(get.call_args.args[1]['vehicleWeight'], 21773)

    def test_invalid_forecast_hour_and_expired_trip(self):
        prefix = '/api/trips/00000000-0000-0000-0000-000000000000/forecast/'
        for value in ['-1', '49', '1.5', 'abc']:
            self.assertEqual(self.client.get(prefix, {'hour': value}).status_code, 400)
        self.assertEqual(self.client.get(prefix).status_code, 404)

    @patch('services.providers.requests.get')
    def test_transport_errors_and_no_secret_leak(self, get):
        get.side_effect = requests.Timeout('https://example.com?key=secret')
        with self.assertRaises(ProviderError) as context:
            get_json('https://example.com', {'key': 'secret'}, 'Provider')
        self.assertEqual(context.exception.status, 504)
        self.assertNotIn('secret', str(context.exception))
        get.side_effect = None
        get.return_value = Mock(status_code=429)
        with self.assertRaises(ProviderError) as context:
            get_json('https://example.com', {}, 'Provider')
        self.assertEqual(context.exception.status, 429)

    @patch('routing.serializers.timezone.now', return_value=datetime(2026, 10, 31, tzinfo=dt_timezone.utc))
    def test_dst_repeated_hour_offsets_remain_distinct(self, now):
        departures = []
        for offset in ['-04:00', '-05:00']:
            serializer = TripSerializer(data={**self.payload, 'departure_at': f'2026-11-01T01:30:00{offset}'})
            self.assertTrue(serializer.is_valid(), serializer.errors)
            departures.append(serializer.validated_data['departure_at'])
        self.assertEqual((departures[1]-departures[0]).total_seconds(), 3600)

    @patch('services.trips.geocode')
    @patch('services.routing.get_json', return_value=route_fixture())
    @patch('services.trips.fetch_forecasts')
    @override_settings(TOMTOM_API_KEY='test-secret')
    def test_unsafe_and_missing_weather_never_recommended_in_pipeline(self, fetch, routing, geocoding):
        geocoding.side_effect = lambda query: {'label': query, 'coordinates': [-96, 32] if 'Dallas' in query else [-95.5, 32.4]}
        start = int(self.departure.timestamp()//3600*3600)
        for mode in ['unsafe', 'missing', 'unsupported-truck']:
            with self.subTest(mode=mode):
                fixture = weather_fixture(wind=55 if mode == 'unsafe' else 10, start=start)
                if mode == 'missing':
                    fixture['hourly']['snowfall'] = [None]*385
                series = normalize_forecast(fixture)
                fetch.side_effect = lambda coords: ({coordinate_key(point): series for point in coords}, [])
                routes = route_fixture()
                if mode == 'unsupported-truck':
                    routes['routes'][0]['sections'][0]['travelMode'] = 'other'
                routing.return_value = routes
                response = self.client.post('/api/routes/calculate/', self.payload, format='json')
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertIsNone(result['recommended_route_id'])
                self.assertFalse(result['routes'][0]['summary']['eligible'])
                self.assertIn('No safe route available.', result['recommendation_reason'])
                if mode == 'unsafe':
                    self.assertAlmostEqual(result['routes'][0]['summary']['risk_miles']['No Travel'], 30)
                if mode == 'missing':
                    self.assertIsNone(result['routes'][0]['summary']['average_risk'])
