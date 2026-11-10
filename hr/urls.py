from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet,
    PayrollSlipViewSet,
    EmployeeMutationViewSet,
    LaborRecordViewSet
)

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('mutations', EmployeeMutationViewSet, basename='employee-mutation')
router.register('labor-records', LaborRecordViewSet, basename='labor-record')
router.register('payroll-slips', PayrollSlipViewSet, basename='payroll-slip')

urlpatterns = [
    path('', include(router.urls)),
]
