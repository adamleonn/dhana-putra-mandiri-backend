from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from core.models import Customer, Supplier, AuditLog
from core.roles import get_user_roles, primary_role
from core.serializers import CustomerSerializer, SupplierSerializer, AuditLogSerializer
from core.permissions import DEFAULT_PERMISSIONS, READ_ALL, DIREKTUR_ONLY, DIREKTUR_ADMIN


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('code')
    serializer_class = CustomerSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': READ_ALL, 'write': DIREKTUR_ADMIN}
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'phone', 'contact_person']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('code')
    serializer_class = SupplierSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': READ_ALL, 'write': DIREKTUR_ADMIN}
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'phone', 'contact_person']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().select_related('actor').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': DIREKTUR_ONLY}
    filterset_fields = ['action', 'model_name', 'actor']
    search_fields = ['object_id', 'object_repr', 'request_id']


class CurrentUserView(APIView):
    """Profil pengguna yang sedang login beserta peran aplikasinya (dari token OIDC)."""
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': READ_ALL}

    def get(self, request):
        user = request.user
        roles = get_user_roles(user)
        return Response({
            'id': user.pk,
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'roles': sorted(roles),
            'primary_role': primary_role(roles),
        })
