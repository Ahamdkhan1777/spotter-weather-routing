from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from redis.exceptions import RedisError


class CacheUnavailableMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, RedisError):
            # Redis exception details can include credentials/hosts. Never echo them.
            return JsonResponse({'error': {'code': 'cache_unavailable',
                                           'message': 'Trip storage is temporarily unavailable. Please retry shortly.'}}, status=503)
        return None
