"""Read optional vehicle dimensions without inventing measurements."""
import math

from django.core.exceptions import ImproperlyConfigured


DIMENSION_FIELDS = (
    ('TRUCK_HEIGHT_M', 'vehicleHeight'),
    ('TRUCK_WIDTH_M', 'vehicleWidth'),
    ('TRUCK_LENGTH_M', 'vehicleLength'),
)


def load_truck_dimensions(environ):
    dimensions = {}
    for variable, parameter in DIMENSION_FIELDS:
        raw = environ.get(variable, '').strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except (ValueError, OverflowError):
            raise ImproperlyConfigured(f'{variable} must be a finite, positive number in metres, or blank.') from None
        if not math.isfinite(value) or value <= 0:
            raise ImproperlyConfigured(f'{variable} must be a finite, positive number in metres, or blank.')
        dimensions[parameter] = value
    return dimensions
