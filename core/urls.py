from rest_framework.routers import DefaultRouter
from django.urls import path
from core.views import CustomerViewSet, SupplierViewSet, AuditLogViewSet, CurrentUserView

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='current-user'),
] + router.urls

