import math

LEVELS = ('Low', 'Moderate', 'High', 'Severe', 'No Travel')
SCORES = {level: index for index, level in enumerate(LEVELS)}


def valid(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def classify_wind(value):
    if not valid(value):
        return 'Unknown'
    return LEVELS[sum(value >= boundary for boundary in (25, 35, 45, 55))]


def classify_rain(value):
    if not valid(value):
        return 'Unknown'
    return 'No Travel' if value > 1 else LEVELS[sum(value >= boundary for boundary in (0.10, 0.25, 0.50))]


def classify_snow(value):
    if not valid(value):
        return 'Unknown'
    return 'No Travel' if value > 3 else LEVELS[sum(value >= boundary for boundary in (0.5, 1, 2))]


def apply_load_rules(wind, load_weight_lb, level):
    if not valid(wind):
        return level, None
    if wind >= 55:
        return 'No Travel', 'Wind at or above 55 mph: No Travel for any load.'
    if wind >= 45 and load_weight_lb > 30000:
        return 'No Travel', 'Wind 45–<55 mph with load above 30,000 lb.'
    if 35 <= wind < 45 and load_weight_lb > 40000:
        return max((level, 'Severe'), key=lambda x: SCORES.get(x, -1)), 'Wind 35–<45 mph with load above 40,000 lb.'
    return level, None


def calculate_checkpoint_risk(weather, load_weight_lb):
    weather = weather or {}
    conditions = {'wind': classify_wind(weather.get('wind_mph')), 'rain': classify_rain(weather.get('rain_in_per_hour')), 'snow': classify_snow(weather.get('snow_in_per_hour'))}
    complete = all(level != 'Unknown' for level in conditions.values())
    base = max(conditions.values(), key=lambda x: SCORES.get(x, -1))
    adjusted, reason = apply_load_rules(weather.get('wind_mph'), load_weight_lb, base)
    if not complete and adjusted != 'No Travel':
        return {'level': 'Unknown', 'complete': False, 'conditions': conditions, 'reason': 'Weather forecast unavailable for this checkpoint/time. Risk coverage is incomplete.'}
    drivers = ', '.join(name for name, level in conditions.items() if level == adjusted)
    return {'level': adjusted, 'complete': complete, 'conditions': conditions,
            'reason': reason or (f'{drivers.capitalize()} determines {adjusted.lower()} risk under the assessment rules.')}


def segment_risk(left, right):
    levels = (left['level'], right['level'])
    if 'No Travel' in levels:
        return 'No Travel'
    if 'Unknown' in levels:
        return 'Unknown'
    return max(levels, key=SCORES.__getitem__)


def calculate_route_risk(checkpoints, truck_supported=True):
    miles = dict.fromkeys((*LEVELS, 'Unknown'), 0.0)
    covered = 0.0
    for left, right in zip(checkpoints, checkpoints[1:]):
        distance = right['distance_miles'] - left['distance_miles']
        if distance < 0:
            raise ValueError('Checkpoint distances must be monotonic.')
        miles[segment_risk(left['risk'], right['risk'])] += distance
        if left['risk']['complete'] and right['risk']['complete']:
            covered += distance
    total = sum(miles.values())
    complete = total > 0 and all(cp['risk']['complete'] for cp in checkpoints)
    blocked = any(cp['risk']['level'] == 'No Travel' for cp in checkpoints)
    return {'risk_miles': miles, 'coverage_percent': covered / total * 100 if total else 0,
            'average_risk': sum(SCORES.get(level, 0)*distance for level, distance in miles.items()) / total if complete else None,
            'complete': complete, 'blocked': blocked, 'eligible': complete and not blocked and truck_supported}
