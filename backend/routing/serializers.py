import math
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers


class AwareDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        try:
            parsed = parse_datetime(value) if isinstance(value, str) else None
        except (ValueError, OverflowError):
            self.fail('invalid', format='ISO 8601 with an explicit UTC offset')
        if parsed is None or timezone.is_naive(parsed):
            raise serializers.ValidationError('Use an ISO 8601 timestamp with an explicit UTC offset.')
        return super().to_internal_value(value)


class LoadWeightField(serializers.FloatField):
    def to_internal_value(self, value):
        if isinstance(value, bool):
            self.fail('invalid')
        return super().to_internal_value(value)


class TripSerializer(serializers.Serializer):
    origin = serializers.CharField(min_length=2, max_length=200)
    destination = serializers.CharField(min_length=2, max_length=200)
    departure_at = AwareDateTimeField()
    load_weight_lb = LoadWeightField(min_value=0.01, max_value=200000)
    interval_miles = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_load_weight_lb(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError('Enter a finite, positive load weight.')
        return value

    def validate_departure_at(self, value):
        now = timezone.now()
        if value < now - timedelta(minutes=5):
            raise serializers.ValidationError('Choose a departure time in the future.')
        if value > now + timedelta(days=15):
            raise serializers.ValidationError('Choose a departure within 15 days. Forecast availability may be shorter.')
        return value

    def validate(self, attrs):
        if attrs['origin'].casefold() == attrs['destination'].casefold():
            raise serializers.ValidationError('Origin and destination must be different.')
        return attrs
