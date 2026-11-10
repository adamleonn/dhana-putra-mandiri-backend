"""
URL configuration for CV Dhana Putra Mandiri (Mini-ERP).
"""
from django.contrib import admin
from django.urls import path, include
from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', health_check, name='api-root'),
    path('api/health/', health_check, name='api-health'),
    path('api/inventory/', include('inventory.urls')),
    path('api/finance/', include('finance.urls')),
    path('api/hr/', include('hr.urls')),
]
