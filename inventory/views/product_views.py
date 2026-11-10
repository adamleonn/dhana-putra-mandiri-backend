from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from config.permissions import StrictRoleBasedAccess
from inventory.models import Product
from inventory.serializers import ProductSerializer
from inventory.services import calculate_abc_classification


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

    @action(detail=False, methods=['get'], url_path='abc-analysis')
    def abc_analysis(self, request):
        data = calculate_abc_classification()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='stock-estimation')
    def stock_estimation(self, request):
        products = Product.objects.filter(is_active=True)
        results = []
        for p in products:
            days = p.estimated_stock_days
            results.append({
                'id': p.id,
                'sku': p.sku,
                'name': p.name,
                'brand': getattr(p, 'brand', 'Lainnya'),
                'package_size': getattr(p, 'package_size', '2L'),
                'uom': p.uom,
                'current_stock': p.current_stock,
                'daily_consumption_rate': p.daily_consumption_rate,
                'estimated_stock_days': round(days, 1) if days is not None else None,
                'is_stock_below_28_days': p.is_stock_below_28_days,
                'abc_class': p.abc_class,
            })
        return Response(results, status=status.HTTP_200_OK)
