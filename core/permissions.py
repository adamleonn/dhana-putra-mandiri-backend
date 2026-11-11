from rest_framework import permissions


def user_in_group(user, group_name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()


def is_direktur(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user_in_group(user, 'Direktur')


class IsDirektur(permissions.BasePermission):
    """
    Super-role: Full CRUD access. Only role authorized to close/reopen accounting periods.
    """
    def has_permission(self, request, view):
        return is_direktur(request.user)


class IsAdminOps(permissions.BasePermission):
    """
    Operational Admin: Draft invoices & deliveries, cash/bank mutations, receive customer payments.
    Forbidden from viewing HPP, profit margin, or General Ledger.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_direktur(request.user) or user_in_group(request.user, 'Admin')


class IsSales(permissions.BasePermission):
    """
    Sales team: Draft SalesInvoice & Delivery.
    Forbidden from viewing HPP/profit/Ledger and forbidden from confirming deliveries.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_direktur(request.user) or user_in_group(request.user, 'Sales') or user_in_group(request.user, 'Admin')


class IsGudang(permissions.BasePermission):
    """
    Warehouse staff: Confirm GoodsReceipt and Delivery.
    All monetary fields are strictly stripped from responses.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_direktur(request.user) or user_in_group(request.user, 'Gudang')


class IsFinance(permissions.BasePermission):
    """
    Finance / Kasir: Cash & bank mutations, AR/AP payments.
    Forbidden from altering physical inventory or creating deliveries.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_direktur(request.user) or user_in_group(request.user, 'Finance') or user_in_group(request.user, 'Admin')


class IsAccounting(permissions.BasePermission):
    """
    Accounting staff: Validates/posts journals, computes HPP, issues DebitNote,
    revises SalesInvoices for shortages, submits period close.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_direktur(request.user) or user_in_group(request.user, 'Accounting')


class IsStakeholderReadOnly(permissions.BasePermission):
    """
    Executive Stakeholder: Strictly read-only access to analytical reports and dashboards.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if user_in_group(request.user, 'Stakeholder'):
            return request.method in permissions.SAFE_METHODS
        return True

