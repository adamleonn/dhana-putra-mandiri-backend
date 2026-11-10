from rest_framework import viewsets, permissions
from config.permissions import StrictRoleBasedAccess
from inventory.models import StockMovement
from inventory.serializers import StockMovementSerializer


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().select_related('product', 'created_by')
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

