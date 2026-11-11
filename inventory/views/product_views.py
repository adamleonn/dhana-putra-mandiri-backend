from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions import IsStakeholderReadOnly, IsDirektur, IsAdminOps
from inventory.models import Product
from inventory.serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().prefetch_related('price_tiers')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['is_active', 'abc_class', 'uom', 'brand']
    search_fields = ['sku', 'name', 'brand']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsDirektur() | IsAdminOps())]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='stock-estimation')
    def stock_estimation(self, request):
        products = self.filter_queryset(self.get_queryset().filter(is_active=True))
        results = []
        for p in products:
            days = p.estimated_days_of_stock
            results.append({
                'id': p.id,
                'sku': p.sku,
                'name': p.name,
                'brand': p.brand,
                'package_size': p.package_size,
                'uom': p.uom,
                'current_stock': str(p.current_stock),
                'daily_consumption_rate': str(p.daily_consumption_rate),
                'estimated_stock_days': float(days),
                'is_stock_below_lead_time': days < p.lead_time_days,
                'lead_time_days': p.lead_time_days,
                'abc_class': p.abc_class,
            })
        return Response(results, status=status.HTTP_200_OK)
