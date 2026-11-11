from rest_framework.routers import DefaultRouter
from core.views import CustomerViewSet, SupplierViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = router.urls

