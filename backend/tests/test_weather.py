from datetime import datetime, timezone
from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase
from services.weather import normalize_forecast, weather_at, fetch_forecasts
from services.providers import ProviderError


def weather_fixture(wind=10, rain=0, snow=0, showers=0, start=1793919600):
    return {'hourly_units': {'time': 'unixtime', 'wind_speed_10m': 'mp/h', 'rain': 'inch', 'showers': 'inch', 'snowfall': 'inch'},
            'hourly': {'time': [start+i*3600 for i in range(385)], 'wind_speed_10m': [wind]*385,
                       'rain': [rain]*385, 'showers': [showers]*385, 'snowfall': [snow]*385}}


class WeatherTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_normalizes_metric_units_and_includes_showers(self):
        fixture = weather_fixture(80.4672, 2.54, 2.54, 2.54)
        fixture['hourly_units'].update(wind_speed_10m='km/h', rain='mm', showers='mm', snowfall='cm')
        row = normalize_forecast(fixture)['rows'][0]
        self.assertAlmostEqual(row['wind_mph'], 50)
        self.assertAlmostEqual(row['rain_in_per_hour'], 0.2)
        self.assertAlmostEqual(row['snow_in_per_hour'], 1)

    def test_selects_arrival_hour_not_departure_and_handles_horizon(self):
        fixture = weather_fixture()
        fixture['hourly']['wind_speed_10m'][1] = 55
        series = normalize_forecast(fixture)
        start = fixture['hourly']['time'][0]
        self.assertEqual(weather_at(series, datetime.fromtimestamp(start+1, timezone.utc))['wind_mph'], 55)
        self.assertEqual(weather_at(series, datetime.fromtimestamp(start, timezone.utc))['wind_mph'], 10)
        self.assertIsNone(weather_at(series, datetime.fromtimestamp(start-1, timezone.utc)))
        self.assertIsNone(weather_at(series, datetime.fromtimestamp(series['times'][-1]+1, timezone.utc)))

    def test_missing_values_are_not_zero(self):
        fixture = weather_fixture()
        fixture['hourly']['snowfall'][0] = None
        self.assertIsNone(normalize_forecast(fixture)['rows'][0]['snow_in_per_hour'])

    def test_unknown_units_and_irregular_times_rejected(self):
        fixture = weather_fixture()
        fixture['hourly_units']['snowfall'] = 'feet'
        with self.assertRaises(ProviderError):
            normalize_forecast(fixture)
        fixture = weather_fixture()
        fixture['hourly']['time'][1] += 5
        with self.assertRaises(ProviderError):
            normalize_forecast(fixture)

    @patch('services.weather.get_json')
    def test_batches_deduplicates_and_caches(self, get):
        get.return_value = [weather_fixture(), weather_fixture()]
        forecasts, warnings = fetch_forecasts([[1, 2], [1, 2], [3, 4]])
        self.assertEqual(len(forecasts), 2)
        self.assertFalse(warnings)
        fetch_forecasts([[1, 2], [3, 4]])
        self.assertEqual(get.call_count, 1)

    @patch('services.weather.get_json', side_effect=ProviderError('Rate limit'))
    def test_provider_failure_is_explicitly_unavailable(self, get):
        forecasts, warnings = fetch_forecasts([[1, 2]])
        self.assertEqual(list(forecasts.values()), [None])
        self.assertEqual(warnings, ['Rate limit'])
