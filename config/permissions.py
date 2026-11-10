from rest_framework import permissions


def user_in_group(user, group_name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()


def is_direktur_or_superuser(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user_in_group(user, 'Direktur')


class IsDirekturOrSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_direktur_or_superuser(request.user)


class CanManageAccountingPeriod(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            is_direktur_or_superuser(request.user)
            or request.user.has_perm('finance.can_manage_accounting_period')
        )


class IsAccountingStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            is_direktur_or_superuser(request.user)
            or user_in_group(request.user, 'Accounting')
            or request.user.has_perm('finance.add_generalledger')
        )


class IsFinanceKasir(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            is_direktur_or_superuser(request.user)
            or user_in_group(request.user, 'Finance')
            or user_in_group(request.user, 'Admin')
            or request.user.has_perm('finance.add_payment')
        )


class IsWarehouseStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            is_direktur_or_superuser(request.user)
            or user_in_group(request.user, 'Gudang')
            or request.user.has_perm('inventory.add_delivery')
        )


class IsSalesStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            is_direktur_or_superuser(request.user)
            or user_in_group(request.user, 'Sales')
            or user_in_group(request.user, 'Admin')
            or request.user.has_perm('finance.add_salesinvoice')
        )


class IsStakeholderReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if user_in_group(request.user, 'Stakeholder'):
            return request.method in permissions.SAFE_METHODS
        return True


class StrictRoleBasedAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if is_direktur_or_superuser(request.user):
            return True
        if user_in_group(request.user, 'Stakeholder'):
            return request.method in permissions.SAFE_METHODS
        return True
