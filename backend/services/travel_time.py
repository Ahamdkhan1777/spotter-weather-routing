"""Validate provider progress and interpolate elapsed time at road-distance targets."""
from bisect import bisect_right
import math


def timing_profile(progress, distance, duration):
    """Return distance/time pairs, or None if the optional profile is unusable.

    TomTom progress distances and times are cumulative route totals. Reject the
    entire profile on missing/non-monotone data; never guess a partial profile.
    """
    if not isinstance(progress, list) or len(progress) < 2:
        return None
    pairs = []
    for point in progress:
        if not isinstance(point, dict):
            return None
        values = (point.get('distanceInMeters'), point.get('travelTimeInSeconds'))
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value < 0 for value in values):
            return None
        meters, seconds = values
        if pairs and (meters <= pairs[-1][0] or seconds < pairs[-1][1]):
            return None
        if meters > distance + 1 or seconds > duration + 1:
            return None
        pairs.append((meters, seconds))
    if pairs[0] != (0, 0):
        return None
    if abs(pairs[-1][0] - distance) > 1 or abs(pairs[-1][1] - duration) > 1:
        return None
    # Provider whole-metre/second rounding must not change the summary endpoint.
    pairs[-1] = (distance, duration)
    if pairs[-2][0] >= distance or pairs[-2][1] > duration:
        return None
    return pairs


class TravelTime:
    def __init__(self, distance, duration, profile=None):
        self.profile = profile or [(0, 0), (distance, duration)]
        self.distances = [point[0] for point in self.profile]

    def at(self, distance):
        if distance <= 0:
            return 0
        if distance >= self.distances[-1]:
            return self.profile[-1][1]
        index = bisect_right(self.distances, distance) - 1
        start, seconds = self.profile[index]
        end, end_seconds = self.profile[index + 1]
        return seconds + (end_seconds - seconds) * (distance - start) / (end - start)
