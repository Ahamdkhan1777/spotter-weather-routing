from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor
import hashlib
import math
from django.conf import settings
from django.core.cache import cache
from .providers import ProviderError, get_json
from .risk_engine import valid


def coordinate_key(coordinates):
    return ','.join(f'{value:.5f}' for value in coordinates)


def normalize_forecast(data):
    """Normalize units from response metadata, never infer units from request flags."""
    try:
        hourly, units = data['hourly'], data['hourly_units']
        factors = {
            'wind_speed_10m': {'mp/h': 1, 'mph': 1, 'km/h': 1/1.609344, 'm/s': 2.2369362921, 'kn': 1.150779448},
            'rain': {'inch': 1, 'mm': 1/25.4},
            'showers': {'inch': 1, 'mm': 1/25.4},
            'snowfall': {'inch': 1, 'cm': 1/2.54, 'mm': 1/25.4},
        }
        conversions = {name: mapping[units[name]] for name, mapping in factors.items()}
        if units['time'] != 'unixtime':
            raise ValueError()
        times = hourly['time']
        if not isinstance(times, list) or not times or any(not isinstance(t, (int, float)) or not math.isfinite(t) for t in times):
            raise ValueError()
        if any(b-a != 3600 for a, b in zip(times, times[1:])):
            raise ValueError()
        for name in conversions:
            if not isinstance(hourly[name], list) or len(hourly[name]) != len(times):
                raise ValueError()
        rows = []
        for i, timestamp in enumerate(times):
            values = {name: hourly[name][i]*factor if valid(hourly[name][i]) else None for name, factor in conversions.items()}
            rows.append({'forecast_at': timestamp, 'wind_mph': values['wind_speed_10m'],
                         'rain_in_per_hour': values['rain']+values['showers'] if values['rain'] is not None and values['showers'] is not None else None,
                         'snow_in_per_hour': values['snowfall']})
        return {'times': times, 'rows': rows}
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ProviderError('Weather returned invalid hourly data or unsupported units.') from None


def weather_at(series, timestamp):
    if not series:
        return None
    epoch = timestamp.timestamp()
    times = series['times']
    # Rain/snow are the preceding-hour accumulation; select the interval ending at ceil(hour).
    if epoch < times[0] or epoch > times[-1]:
        return None
    index = bisect_left(times, epoch)
    return series['rows'][index]


def fetch_forecasts(coordinates):
    unique = {coordinate_key(p): p for p in coordinates}
    if len(unique) > settings.MAX_WEATHER_LOCATIONS:
        raise ProviderError(f'This trip needs {len(unique)} forecast locations; the limit is {settings.MAX_WEATHER_LOCATIONS}. Choose a larger checkpoint interval or a shorter trip.', 'sampling_limit', 422)
    forecasts, missing, warnings = {}, [], []
    scope = hashlib.sha256(settings.WEATHER_API_URL.encode()).hexdigest()[:12]
    for key, point in unique.items():
        cached = cache.get(f'weather:{scope}:{key}')
        if cached is None:
            missing.append((key, point))
        else:
            forecasts[key] = cached
    batches = [missing[i:i+25] for i in range(0, len(missing), 25)]

    def fetch_batch(batch):
        params = {'latitude': ','.join(str(p[1]) for _, p in batch), 'longitude': ','.join(str(p[0]) for _, p in batch),
                  'hourly': 'wind_speed_10m,rain,showers,snowfall', 'wind_speed_unit': 'mph',
                  'precipitation_unit': 'inch', 'timezone': 'UTC', 'timeformat': 'unixtime', 'forecast_days': 16}
        if settings.OPEN_METEO_API_KEY:
            params['apikey'] = settings.OPEN_METEO_API_KEY
        try:
            data = get_json(settings.WEATHER_API_URL, params, 'Open-Meteo')
            data = [data] if isinstance(data, dict) else data
            if len(data) != len(batch):
                raise ProviderError('Weather returned an unexpected number of locations.')
            result, errors = {}, []
            for (key, _), location in zip(batch, data):
                try:
                    result[key] = normalize_forecast(location)
                    cache.set(f'weather:{scope}:{key}', result[key], 900)
                except ProviderError as error:
                    result[key] = None
                    errors.append(str(error))
            return result, errors
        except ProviderError as error:
            return {key: None for key, _ in batch}, [str(error)]

    with ThreadPoolExecutor(max_workers=3) as pool:
        for result, errors in pool.map(fetch_batch, batches):
            forecasts.update(result)
            warnings.extend(errors)
    return forecasts, list(dict.fromkeys(warnings))
