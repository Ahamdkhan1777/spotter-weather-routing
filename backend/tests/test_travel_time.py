from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from services.checkpoints import METERS_PER_MILE, RouteGeometry, generate_checkpoints
from services.routing import calculate_routes
from services.travel_time import TravelTime, timing_profile
from tests.test_api import route_fixture
from services.trips import calculate_trip
from services.weather import normalize_forecast, coordinate_key
from tests.test_weather import weather_fixture


class TravelTimeTests(SimpleTestCase):
    def setUp(self):
        self.distance = 100 * METERS_PER_MILE
        self.duration = 7200
        self.progress = [
            {'distanceInMeters': 0, 'travelTimeInSeconds': 0},
            {'distanceInMeters': 50 * METERS_PER_MILE, 'travelTimeInSeconds': 5400},
            {'distanceInMeters': self.distance, 'travelTimeInSeconds': self.duration},
        ]

    def test_uneven_speeds_and_exact_timing_boundaries(self):
        profile = timing_profile(self.progress, self.distance, self.duration)
        timing = TravelTime(self.distance, self.duration, profile)
        for miles, seconds in [(0, 0), (25, 2700), (50, 5400), (75, 6300), (100, 7200)]:
            self.assertAlmostEqual(timing.at(miles * METERS_PER_MILE), seconds)

    def test_checkpoint_pipeline_uses_profile_and_preserves_summary_eta(self):
        geometry = RouteGeometry([[0, 0], [1, 0]], self.distance)
        departure = datetime(2026, 11, 7, 23, tzinfo=timezone.utc)
        profile = timing_profile(self.progress, self.distance, self.duration)
        points = generate_checkpoints(geometry, 25, self.duration, departure, 'r', profile)
        self.assertEqual([(datetime.fromisoformat(cp['eta']) - departure).total_seconds() for cp in points],
                         [0, 2700, 5400, 6300, 7200])
        self.assertEqual(points[-1]['coordinates'], [1, 0])

    def test_missing_profile_preserves_existing_fallback(self):
        for progress in [None, [], {}, [self.progress[0]]]:
            self.assertIsNone(timing_profile(progress, self.distance, self.duration))
        self.assertEqual(TravelTime(self.distance, self.duration).at(self.distance / 4), 1800)

    @override_settings(TOMTOM_API_KEY='isolated-test-key')
    @patch('services.trips.geocode')
    @patch('services.routing.get_json')
    @patch('services.trips.fetch_forecasts')
    def test_arrival_weather_uses_provider_timing_not_uniform_speed(self, fetch, routing, geocode):
        departure = datetime(2026, 11, 7, 12, 20, tzinfo=timezone.utc)
        fixture = route_fixture()
        fixture['routes'][0]['summary']['travelTimeInSeconds'] = 7200
        fixture['routes'][0]['progress'] = [
            {'distanceInMeters': 0, 'travelTimeInSeconds': 0},
            {'distanceInMeters': 10 * METERS_PER_MILE, 'travelTimeInSeconds': 5400},
            {'distanceInMeters': 30 * METERS_PER_MILE, 'travelTimeInSeconds': 7200},
        ]
        routing.return_value = fixture
        geocode.side_effect = lambda query: {'label': query, 'coordinates': [-96, 32] if query == 'Dallas' else [-95.5, 32.4]}
        weather = weather_fixture(start=int(departure.replace(minute=0).timestamp()))
        weather['hourly']['wind_speed_10m'][3] = 55
        series = normalize_forecast(weather)
        fetch.side_effect = lambda coords: ({coordinate_key(point): series for point in coords}, [])
        result = calculate_trip({'origin': 'Dallas', 'destination': 'Tyler', 'departure_at': departure,
                                 'load_weight_lb': 10000, 'interval_miles': 25})
        checkpoint = result['routes'][0]['checkpoints'][1]
        self.assertEqual(datetime.fromisoformat(checkpoint['eta']), departure + timedelta(seconds=6750))
        self.assertEqual(checkpoint['weather']['wind_mph'], 55)
        self.assertEqual(checkpoint['risk']['level'], 'No Travel')
        self.assertIsNone(result['recommended_route_id'])

    def test_invalid_profiles_are_rejected_as_a_whole(self):
        for field, value in [('distanceInMeters', None), ('distanceInMeters', True),
                             ('distanceInMeters', float('nan')), ('distanceInMeters', 0),
                             ('travelTimeInSeconds', float('inf')), ('travelTimeInSeconds', -1),
                             ('travelTimeInSeconds', 8000), ('travelTimeInSeconds', '5400')]:
            with self.subTest(field=field, value=value):
                progress = deepcopy(self.progress)
                progress[1][field] = value
                self.assertIsNone(timing_profile(progress, self.distance, self.duration))
        for index, field, value in [(0, 'distanceInMeters', 1), (0, 'travelTimeInSeconds', 1),
                                   (2, 'distanceInMeters', self.distance - 10), (2, 'travelTimeInSeconds', 7190),
                                   (1, 'travelTimeInSeconds', 7300)]:
            progress = deepcopy(self.progress)
            progress[index][field] = value
            self.assertIsNone(timing_profile(progress, self.distance, self.duration))
        self.assertIsNone(timing_profile([self.progress[0], None], self.distance, self.duration))

    def test_plateaus_are_valid_and_endpoint_rounding_preserves_total(self):
        progress = deepcopy(self.progress)
        progress[1]['travelTimeInSeconds'] = 0
        progress[-1] = {'distanceInMeters': round(self.distance), 'travelTimeInSeconds': 7200}
        timing = TravelTime(self.distance, self.duration, timing_profile(progress, self.distance, self.duration))
        self.assertEqual(timing.at(self.distance / 4), 0)
        self.assertEqual(timing.at(self.distance), 7200)

    @override_settings(TOMTOM_API_KEY='isolated-test-key')
    @patch('services.routing.get_json')
    def test_provider_parameters_and_profile_are_used(self, get):
        fixture = route_fixture()
        fixture['routes'][0]['progress'] = [
            {'distanceInMeters': 0, 'travelTimeInSeconds': 0},
            {'distanceInMeters': 10 * METERS_PER_MILE, 'travelTimeInSeconds': 2400},
            {'distanceInMeters': 30 * METERS_PER_MILE, 'travelTimeInSeconds': 3600},
        ]
        get.return_value = fixture
        routes, warnings = calculate_routes({'coordinates': [0, 0]}, {'coordinates': [1, 1]},
                                           datetime(2026, 11, 7, tzinfo=timezone.utc), 10000)
        self.assertEqual(get.call_args.args[1]['extendedRouteRepresentation'], ['distance', 'travelTime'])
        self.assertIsNotNone(routes[0]['timing'])
        self.assertFalse(any('uniform-speed' in warning for warning in warnings))
        fixture['routes'][0]['progress'][1]['travelTimeInSeconds'] = -1
        routes, warnings = calculate_routes({'coordinates': [0, 0]}, {'coordinates': [1, 1]},
                                           datetime(2026, 11, 7, tzinfo=timezone.utc), 10000)
        self.assertIsNone(routes[0]['timing'])
        self.assertTrue(any('uniform-speed' in warning for warning in warnings))
