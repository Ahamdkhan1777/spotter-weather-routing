from django.test import SimpleTestCase
from services.risk_engine import classify_wind, classify_rain, classify_snow, calculate_checkpoint_risk, calculate_route_risk
from services.recommendation import recommend


def checkpoint(distance, level='Low', complete=True):
    return {'distance_miles': distance, 'risk': {'level': level, 'complete': complete}}


class RiskTests(SimpleTestCase):
    def test_wind_boundaries(self):
        for value, expected in [(24.99, 'Low'), (25, 'Moderate'), (34, 'Moderate'), (34.99, 'Moderate'), (35, 'High'), (44, 'High'), (44.99, 'High'), (45, 'Severe'), (54, 'Severe'), (54.99, 'Severe'), (55, 'No Travel')]:
            with self.subTest(value=value):
                self.assertEqual(classify_wind(value), expected)

    def test_rain_boundaries(self):
        for value, expected in [(0.09, 'Low'), (0.10, 'Moderate'), (0.2499, 'Moderate'), (0.25, 'High'), (0.50, 'Severe'), (1, 'Severe'), (1.01, 'No Travel')]:
            with self.subTest(value=value):
                self.assertEqual(classify_rain(value), expected)

    def test_snow_boundaries(self):
        for value, expected in [(0.49, 'Low'), (0.50, 'Moderate'), (1, 'High'), (2, 'Severe'), (3, 'Severe'), (3.01, 'No Travel')]:
            with self.subTest(value=value):
                self.assertEqual(classify_snow(value), expected)

    def test_load_boundaries(self):
        for wind, load, expected in [(50, 30000, 'Severe'), (50, 30001, 'No Travel'), (40, 40000, 'High'), (40, 40001, 'Severe'), (55, 1, 'No Travel'), (55, 100000, 'No Travel'), (44.99, 40001, 'Severe'), (54.99, 30001, 'No Travel')]:
            with self.subTest(wind=wind, load=load):
                result = calculate_checkpoint_risk({'wind_mph': wind, 'rain_in_per_hour': 0, 'snow_in_per_hour': 0}, load)
                self.assertEqual(result['level'], expected)

    def test_highest_condition_wins(self):
        self.assertEqual(calculate_checkpoint_risk({'wind_mph': 40, 'rain_in_per_hour': 1.1, 'snow_in_per_hour': 0}, 45000)['level'], 'No Travel')

    def test_invalid_or_missing_weather_is_unknown(self):
        for invalid in [None, -1, float('nan'), float('inf'), '0', True]:
            with self.subTest(value=invalid):
                self.assertEqual(classify_wind(invalid), 'Unknown')
                self.assertEqual(calculate_checkpoint_risk({'wind_mph': 0, 'rain_in_per_hour': invalid, 'snow_in_per_hour': 0}, 100)['level'], 'Unknown')

    def test_known_no_travel_is_preserved_when_other_weather_missing(self):
        result = calculate_checkpoint_risk({'wind_mph': 55}, 100)
        self.assertEqual(result['level'], 'No Travel')
        self.assertFalse(result['complete'])

    def test_distance_weighting_and_partial_interval(self):
        summary = calculate_route_risk([checkpoint(0), checkpoint(25), checkpoint(50, 'High'), checkpoint(67, 'Severe')])
        self.assertEqual(summary['risk_miles']['Low'], 25)
        self.assertEqual(summary['risk_miles']['High'], 25)
        self.assertEqual(summary['risk_miles']['Severe'], 17)
        self.assertAlmostEqual(summary['average_risk'], (25*2+17*3)/67)
        self.assertEqual(sum(summary['risk_miles'].values()), 67)

    def test_incomplete_coverage_blocks_recommendation(self):
        result = calculate_route_risk([checkpoint(0), checkpoint(25, 'Unknown', False), checkpoint(50)])
        self.assertEqual(result['risk_miles']['Unknown'], 50)
        self.assertIsNone(result['average_risk'])
        self.assertFalse(result['eligible'])

    def test_no_travel_endpoint_blocks_adjacent_segment(self):
        result = calculate_route_risk([checkpoint(0), checkpoint(10, 'No Travel')])
        self.assertEqual(result['risk_miles']['No Travel'], 10)
        self.assertFalse(result['eligible'])

    def test_uniform_risk_is_sampling_independent(self):
        for interval in [10, 25, 50]:
            distances = [*range(0, 117, interval), 117]
            result = calculate_route_risk([checkpoint(distance, 'High') for distance in distances])
            self.assertEqual(result['risk_miles']['High'], 117)
            self.assertEqual(result['average_risk'], 2)


class RecommendationTests(SimpleTestCase):
    def route(self, identifier, severe=0, high=0, average=0, duration=1, eligible=True, blocked=False):
        return {'id': identifier, 'duration_seconds': duration, 'summary': {'eligible': eligible, 'blocked': blocked,
                'risk_miles': {'Severe': severe, 'High': high}, 'average_risk': average}}

    def test_ranking_priorities(self):
        pairs = [
            (self.route('a', severe=1, duration=100), self.route('b', severe=2)),
            (self.route('a', high=1, duration=100), self.route('b', high=2)),
            (self.route('a', average=1, duration=100), self.route('b', average=2)),
            (self.route('a', duration=1), self.route('b', duration=2)),
        ]
        for first, second in pairs:
            self.assertEqual(recommend([second, first])[0], 'a')

    def test_ineligible_route_cannot_win(self):
        self.assertEqual(recommend([self.route('unsafe', eligible=False, blocked=True), self.route('safe', severe=10)])[0], 'safe')
        self.assertEqual(recommend([self.route('unknown', eligible=False), self.route('safe')])[0], 'safe')

    def test_all_unsafe(self):
        identifier, reason = recommend([self.route('unsafe', eligible=False, blocked=True)])
        self.assertIsNone(identifier)
        self.assertIn('No safe route available.', reason)

    def test_ties_are_deterministic(self):
        self.assertEqual(recommend([self.route('b'), self.route('a')])[0], 'a')
