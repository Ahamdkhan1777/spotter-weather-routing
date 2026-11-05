from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health),
    path('places/', views.places),
    path('routes/calculate/', views.calculate),
    path('trips/<uuid:trip_id>/', views.detail),
    path('trips/<uuid:trip_id>/forecast/', views.forecast),
]
