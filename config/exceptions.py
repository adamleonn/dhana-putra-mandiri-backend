from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal


class InsufficientStockError(Exception):
    def __init__(self, message: str, product_sku: str, product_name: str, requested_qty: Decimal, available_stock: Decimal):
        super().__init__(message)
        self.message = message
        self.product_sku = product_sku
        self.product_name = product_name
        self.requested_qty = requested_qty
        self.available_stock = available_stock


class PeriodClosedError(Exception):
    def __init__(self, message: str, period_name: str = ''):
        super().__init__(message)
        self.message = message
        self.period_name = period_name


class DuplicatePostingError(Exception):
    def __init__(self, message: str, reference: str = ''):
        super().__init__(message)
        self.message = message
        self.reference = reference


def custom_exception_handler(exc, context):
    """
    Standardized Enterprise API exception handler.
    Guarantees stable contract: { "code": str, "message": str, "details": dict }
    """
    if isinstance(exc, InsufficientStockError):
        return Response(
            {
                'code': 'INSUFFICIENT_STOCK',
                'message': str(exc.message),
                'details': {
                    'sku': exc.product_sku,
                    'product_name': exc.product_name,
                    'requested_qty': str(exc.requested_qty),
                    'available_stock': str(exc.available_stock)
                }
            },
            status=status.HTTP_409_CONFLICT
        )

    if isinstance(exc, PeriodClosedError):
        return Response(
            {
                'code': 'ACCOUNTING_PERIOD_LOCKED',
                'message': str(exc.message),
                'details': {
                    'period': exc.period_name
                }
            },
            status=status.HTTP_423_LOCKED
        )

    if isinstance(exc, DuplicatePostingError):
        return Response(
            {
                'code': 'DUPLICATE_POSTING',
                'message': str(exc.message),
                'details': {
                    'reference': exc.reference
                }
            },
            status=status.HTTP_409_CONFLICT
        )

    # Fallback to DRF standard handler
    response = exception_handler(exc, context)
    if response is not None:
        custom_data = {
            'code': getattr(exc, 'default_code', 'ERROR').upper(),
            'message': 'Permintaan tidak valid atau terjadi kesalahan operasional.',
            'details': response.data
        }
        response.data = custom_data

    return response

