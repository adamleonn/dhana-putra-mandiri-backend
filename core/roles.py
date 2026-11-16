"""
Definisi peran aplikasi (sumber tunggal kebenaran).

Peran aktif hanya empat: direktur, admin, gudang, stakeholder.
Setiap peran dipetakan ke Django Group dengan nama kapital (mis. 'Direktur')
agar data role pengguna yang sudah ada tetap berlaku.
"""

from __future__ import annotations

DIREKTUR = 'direktur'
ADMIN = 'admin'
GUDANG = 'gudang'
STAKEHOLDER = 'stakeholder'

ALL_ROLES = frozenset({DIREKTUR, ADMIN, GUDANG, STAKEHOLDER})

ROLE_TO_GROUP = {
    DIREKTUR: 'Direktur',
    ADMIN: 'Admin',
    GUDANG: 'Gudang',
    STAKEHOLDER: 'Stakeholder',
}
GROUP_TO_ROLE = {group: role for role, group in ROLE_TO_GROUP.items()}

# Atribut cache pada objek user (diisi oleh OIDCAuthentication per-request).
_CACHE_ATTR = '_app_roles'


def get_user_roles(user) -> frozenset[str]:
    """Kembalikan himpunan peran aplikasi milik user (kosong bila tidak ada)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return frozenset()
    cached = getattr(user, _CACHE_ATTR, None)
    if cached is not None:
        return cached
    names = user.groups.filter(name__in=ROLE_TO_GROUP.values()).values_list('name', flat=True)
    roles = frozenset(GROUP_TO_ROLE[name] for name in names)
    setattr(user, _CACHE_ATTR, roles)
    return roles


def set_cached_roles(user, roles) -> None:
    setattr(user, _CACHE_ATTR, frozenset(roles))


def has_role(user, *roles: str) -> bool:
    return bool(get_user_roles(user) & set(roles))


def is_direktur(user) -> bool:
    return has_role(user, DIREKTUR)


def primary_role(roles) -> str | None:
    """Peran utama untuk tampilan (prioritas: direktur > admin > gudang > stakeholder)."""
    for role in (DIREKTUR, ADMIN, GUDANG, STAKEHOLDER):
        if role in roles:
            return role
    return None
