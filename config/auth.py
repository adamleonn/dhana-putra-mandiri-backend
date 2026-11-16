"""
Autentikasi DRF berbasis OAuth 2.0 Bearer access token (JWT) dari identity
provider OpenID Connect (mis. Keycloak).

Autentikasi token demo `demo-*` telah DIHAPUS. Satu-satunya cara mengakses
API adalah access token yang ditandatangani IdP dan lolos validasi
`config.oidc.validate_access_token`.

Penyediaan & sinkronisasi pengguna:
1. Cari user berdasarkan (oidc_issuer, oidc_subject).
2. Bila belum ada dan OIDC_LINK_EXISTING_BY_USERNAME aktif, tautkan ke user
   lama yang username-nya sama dan belum tertaut (migrasi pengguna lama).
3. Bila tetap belum ada dan OIDC_AUTO_CREATE_USERS aktif, buat user baru
   (tanpa password lokal).
4. Group peran (Direktur/Admin/Gudang/Stakeholder) disinkronkan dari klaim
   role token pada setiap request; IdP adalah sumber kebenaran peran.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from rest_framework import authentication, exceptions

from config.oidc import OIDCSettings, TokenValidationError, extract_app_roles, validate_access_token
from core.roles import ROLE_TO_GROUP, set_cached_roles

logger = logging.getLogger('audit')


class OIDCAuthentication(authentication.BaseAuthentication):
    keyword = 'bearer'

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()
        if not auth_header or auth_header[0].lower() != self.keyword.encode():
            return None
        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Header Authorization Bearer tidak valid.')
        try:
            token = auth_header[1].decode('ascii')
        except UnicodeError as exc:
            raise exceptions.AuthenticationFailed('Token Bearer tidak valid.') from exc

        cfg = OIDCSettings.from_django()
        try:
            claims = validate_access_token(token, cfg)
        except TokenValidationError as exc:
            raise exceptions.AuthenticationFailed(str(exc)) from exc

        roles = extract_app_roles(claims, cfg)
        user = self._get_or_provision_user(claims, cfg)
        if not user.is_active:
            raise exceptions.AuthenticationFailed('Akun pengguna telah dinonaktifkan.')

        self._sync_roles(user, roles)
        set_cached_roles(user, roles)
        return (user, claims)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

    # ------------------------------------------------------------------ users

    def _get_or_provision_user(self, claims: dict, cfg: OIDCSettings):
        User = get_user_model()
        issuer = claims['iss']
        subject = str(claims['sub'])
        username = (claims.get('preferred_username') or '').strip() or subject
        email = (claims.get('email') or '').strip()

        user = User.objects.filter(oidc_issuer=issuer, oidc_subject=subject).first()

        if user is None and settings.OIDC_LINK_EXISTING_BY_USERNAME:
            candidate = User.objects.filter(username=username).first()
            if candidate is not None:
                if candidate.oidc_subject and (candidate.oidc_subject != subject or candidate.oidc_issuer != issuer):
                    logger.warning('OIDC identity conflict for username=%s', username)
                    raise exceptions.AuthenticationFailed('Identitas pengguna bentrok dengan akun lain.')
                candidate.oidc_issuer = issuer
                candidate.oidc_subject = subject
                candidate.save(update_fields=['oidc_issuer', 'oidc_subject'])
                logger.info('OIDC linked existing user id=%s username=%s', candidate.pk, username)
                user = candidate

        if user is None:
            if not settings.OIDC_AUTO_CREATE_USERS:
                raise exceptions.AuthenticationFailed('Pengguna belum terdaftar pada aplikasi.')
            if User.objects.filter(username=username).exists():
                raise exceptions.AuthenticationFailed('Identitas pengguna bentrok dengan akun lain.')
            try:
                with transaction.atomic():
                    user = User(
                        username=username,
                        email=email,
                        first_name=(claims.get('given_name') or '')[:150],
                        last_name=(claims.get('family_name') or '')[:150],
                        oidc_issuer=issuer,
                        oidc_subject=subject,
                    )
                    user.set_unusable_password()
                    user.save()
                logger.info('OIDC provisioned user id=%s username=%s', user.pk, username)
            except IntegrityError:
                # Request paralel pertama kali login: ambil yang sudah dibuat.
                user = User.objects.get(oidc_issuer=issuer, oidc_subject=subject)
        else:
            changed = []
            for field, value in (
                ('email', email),
                ('first_name', (claims.get('given_name') or '')[:150]),
                ('last_name', (claims.get('family_name') or '')[:150]),
            ):
                if value and getattr(user, field) != value:
                    setattr(user, field, value)
                    changed.append(field)
            if changed:
                user.save(update_fields=changed)
        return user

    def _sync_roles(self, user, roles: set[str]) -> None:
        wanted = {ROLE_TO_GROUP[r] for r in roles}
        current = set(user.groups.filter(name__in=ROLE_TO_GROUP.values()).values_list('name', flat=True))
        if wanted == current:
            return
        to_add = wanted - current
        to_remove = current - wanted
        if to_add:
            groups = [Group.objects.get_or_create(name=name)[0] for name in to_add]
            user.groups.add(*groups)
        if to_remove:
            user.groups.remove(*Group.objects.filter(name__in=to_remove))
        logger.info('OIDC role sync user id=%s roles=%s', user.pk, sorted(roles))
