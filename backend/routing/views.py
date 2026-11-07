from django.conf import settings
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from services.geocoding import search_places
from services.providers import ProviderError
from services.trips import calculate_trip, forecast_for_trip, get_trip
from .serializers import TripSerializer


def provider_response(action):
    try:
        return Response(action())
    except ProviderError as error:
        return Response({'error': {'code': error.code, 'message': str(error)}}, status=error.status)


@api_view(['GET'])
@throttle_classes([])
def health(request):
    return Response({'status': 'ok', 'routing_configured': bool(settings.TOMTOM_API_KEY), 'weather_provider': 'Open-Meteo', 'demo_mode': False})


@api_view(['GET'])
def places(request):
    query = request.query_params.get('q', '').strip()
    if not 2 <= len(query) <= 200:
        return Response({'error': {'code': 'invalid_query', 'message': 'Enter 2–200 characters.'}}, status=400)
    return provider_response(lambda: {'places': search_places(query)})


@api_view(['POST'])
def calculate(request):
    serializer = TripSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return provider_response(lambda: calculate_trip(serializer.validated_data))


@api_view(['GET'])
def detail(request, trip_id):
    return provider_response(lambda: get_trip(trip_id)['result'])


@api_view(['GET'])
@throttle_classes([])
def forecast(request, trip_id):
    raw = request.query_params.get('hour', '0')
    if not (1 <= len(raw) <= 2 and raw.isascii() and raw.isdecimal()) or not 0 <= int(raw) <= 48:
        return Response({'error': {'code': 'invalid_hour', 'message': 'Forecast hour must be an integer from 0 to 48.'}}, status=400)
    return provider_response(lambda: forecast_for_trip(trip_id, int(raw)))
