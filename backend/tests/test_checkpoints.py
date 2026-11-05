from datetime import datetime, timezone
from django.test import SimpleTestCase
from services.checkpoints import METERS_PER_MILE, RouteGeometry, generate_checkpoints, haversine
from services.providers import ProviderError


class CheckpointTests(SimpleTestCase):
    def setUp(self):
        self.departure = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)
        self.geometry = RouteGeometry([[0, 0], [0.5, 0], [1, 0], [1, 1]], 117*METERS_PER_MILE)

    def test_intervals_include_origin_partial_and_destination(self):
        for interval in [10, 25, 50]:
            with self.subTest(interval=interval):
                points = generate_checkpoints(self.geometry, interval, 7200, self.departure, 'r')
                expected = [*range(0, 117, interval), 117]
                self.assertEqual(len(points), len(expected))
                for point, distance in zip(points, expected):
                    self.assertAlmostEqual(point['distance_miles'], distance, places=8)
                self.assertEqual(points[0]['coordinates'], [0, 0])
                self.assertEqual(points[-1]['coordinates'], [1, 1])
                self.assertEqual(datetime.fromisoformat(points[-1]['eta']).hour, 1)
                self.assertEqual(datetime.fromisoformat(points[-1]['eta']).day, 6)

    def test_exact_multiple_does_not_duplicate_destination(self):
        geometry = RouteGeometry([[0, 0], [1, 0]], 50*METERS_PER_MILE)
        self.assertEqual(len(generate_checkpoints(geometry, 25, 3600, self.departure, 'r')), 3)

    def test_positions_follow_road_and_slice_preserves_vertices(self):
        point = self.geometry.position(self.geometry.total*0.75)
        self.assertAlmostEqual(point[0], 1, places=5)
        segment = self.geometry.slice(0, self.geometry.total)
        self.assertIn([0.5, 0], segment)
        self.assertIn([1, 0], segment)

    def test_eta_is_proportional_to_cumulative_distance(self):
        points = generate_checkpoints(self.geometry, 25, 11700, self.departure, 'r')
        self.assertAlmostEqual((datetime.fromisoformat(points[1]['eta'])-self.departure).total_seconds(), 2500)

    def test_invalid_geometry_and_duration(self):
        for coordinates, distance in [([], 100), ([[0, 0], [0, 0]], 100), ([[181, 0], [0, 0]], 100), ([[0, 0], [1, 0]], 0)]:
            with self.assertRaises(ProviderError):
                RouteGeometry(coordinates, distance)
        with self.assertRaises(ProviderError):
            generate_checkpoints(self.geometry, 25, float('nan'), self.departure, 'r')

    def test_antimeridian(self):
        geometry = RouteGeometry([[179, 10], [-179, 10]], 100)
        middle = geometry.position(50)
        self.assertAlmostEqual(abs(middle[0]), 180)
        self.assertLess(haversine([179, 10], [-179, 10]), 250000)
