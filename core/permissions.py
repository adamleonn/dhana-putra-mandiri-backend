"""
Kontrol akses berbasis peran (RBAC) untuk seluruh endpoint API.

Setiap ViewSet mendeklarasikan `role_access`, contoh:

    role_access = {
        'read':  ALL_ROLES,              # GET/HEAD/OPTIONS
        'write': {DIREKTUR, ADMIN},      # POST/PUT/PATCH/DELETE
        'confirm': {DIREKTUR, GUDANG},   # override per action
    }

Prinsip:
- Deny-by-default: view tanpa `role_access` ditolak.
- User tanpa satu pun dari empat peran aplikasi selalu ditolak (403).
- Peran berasal dari klaim token IdP (disinkronkan ke Django Group).
"""

from rest_framework import permissions

from core.roles import ADMIN, ALL_ROLES, DIREKTUR, GUDANG, STAKEHOLDER, get_user_roles

__all__ = [
    'RoleBasedAccess', 'ALL_ROLES', 'DIREKTUR', 'ADMIN', 'GUDANG', 'STAKEHOLDER',
    'READ_ALL', 'MANAGEMENT', 'DIREKTUR_ONLY', 'DIREKTUR_ADMIN',
]

READ_ALL = ALL_ROLES
MANAGEMENT = frozenset({DIREKTUR, ADMIN, STAKEHOLDER})  # boleh melihat nilai finansial
DIREKTUR_ONLY = frozenset({DIREKTUR})
DIREKTUR_ADMIN = frozenset({DIREKTUR, ADMIN})


class RoleBasedAccess(permissions.BasePermission):
    message = 'Peran Anda tidak memiliki akses ke sumber daya ini.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        roles = get_user_roles(user)
        if not roles:
            self.message = 'Akun Anda belum memiliki peran aplikasi. Hubungi administrator.'
            return False

        policy = getattr(view, 'role_access', None)
        if not policy:
            return False

        action = getattr(view, 'action', None)
        if action and action in policy:
            allowed = policy[action]
        elif request.method in permissions.SAFE_METHODS:
            allowed = policy.get('read', ())
        else:
            allowed = policy.get('write', ())
        return bool(roles & set(allowed))


DEFAULT_PERMISSIONS = [permissions.IsAuthenticated, RoleBasedAccess]
