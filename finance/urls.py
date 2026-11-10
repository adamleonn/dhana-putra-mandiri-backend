from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChartOfAccountsViewSet,
    AccountingPeriodViewSet,
    GeneralLedgerViewSet,
    SalesInvoiceViewSet,
    DebitNoteViewSet,
    PaymentViewSet,
    FinancialReportsViewSet,
    CustomerViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register('customers', CustomerViewSet, basename='customer')
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('chart-of-accounts', ChartOfAccountsViewSet, basename='chart-of-accounts')
router.register('accounting-periods', AccountingPeriodViewSet, basename='accounting-period')
router.register('general-ledger', GeneralLedgerViewSet, basename='general-ledger')
router.register('sales-invoices', SalesInvoiceViewSet, basename='sales-invoice')
router.register('debit-notes', DebitNoteViewSet, basename='debit-note')
router.register('payments', PaymentViewSet, basename='payment')
router.register('reports', FinancialReportsViewSet, basename='financial-report')

urlpatterns = [
    path('', include(router.urls)),
]
