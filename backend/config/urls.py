from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.urls import include, path


def frontend(request):
    index = settings.BASE_DIR.parent / 'frontend' / 'dist' / 'index.html'
    if not index.is_file():
        return JsonResponse({'message': 'Run the Vite frontend at http://127.0.0.1:5173, or build frontend/dist for production.'})
    return FileResponse(index.open('rb'), content_type='text/html')


urlpatterns = [path('api/', include('routing.urls')), path('', frontend)]
