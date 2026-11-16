"""
Validasi access token OAuth 2.0 / OpenID Connect (JWT) terhadap identity provider.

- Kunci publik diambil dari `jwks_uri` pada discovery document OIDC
  (`<issuer>/.well-known/openid-configuration`) dan di-cache dengan TTL.
- Kunci tidak dikenal (rotasi kunci IdP) memicu satu kali refetch JWKS
  dengan rate-limit, sehingga token palsu tidak bisa memaksa fetch berulang.
- Diverifikasi: signature (algoritma allowlist), issuer, audience, exp, nbf,
  iat, subject, dan (opsional) authorized party (`azp`).
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from joserfc import jwt
from joserfc.errors import ExpiredTokenError, JoseError
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry

from core.roles import ALL_ROLES

logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    """Token ditolak. Pesan aman untuk dikembalikan ke klien."""


@dataclass(frozen=True)
class OIDCSettings:
    issuer: str
    audience: str
    discovery_url: str
    jwks_url: str | None
    algorithms: tuple[str, ...]
    allowed_azp: tuple[str, ...]
    role_claim_paths: tuple[str, ...]
    role_mapping: dict[str, str]
    leeway: int
    jwks_cache_ttl: int
    http_timeout: float

    @classmethod
    def from_django(cls) -> 'OIDCSettings':
        issuer = (getattr(settings, 'OIDC_ISSUER', '') or '').rstrip('/')
        audience = getattr(settings, 'OIDC_API_AUDIENCE', '') or ''
        if not issuer or not audience:
            raise ImproperlyConfigured('OIDC_ISSUER dan OIDC_API_AUDIENCE wajib dikonfigurasi.')
        discovery = getattr(settings, 'OIDC_DISCOVERY_URL', '') or f'{issuer}/.well-known/openid-configuration'
        return cls(
            issuer=issuer,
            audience=audience,
            discovery_url=discovery,
            jwks_url=getattr(settings, 'OIDC_JWKS_URL', '') or None,
            algorithms=tuple(settings.OIDC_ALLOWED_ALGORITHMS),
            allowed_azp=tuple(settings.OIDC_ALLOWED_CLIENT_IDS),
            role_claim_paths=tuple(settings.OIDC_ROLE_CLAIM_PATHS),
            role_mapping=dict(settings.OIDC_ROLE_MAPPING),
            leeway=int(settings.OIDC_LEEWAY_SECONDS),
            jwks_cache_ttl=int(settings.OIDC_JWKS_CACHE_SECONDS),
            http_timeout=float(settings.OIDC_HTTP_TIMEOUT_SECONDS),
        )


def _assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == 'https':
        return
    if parsed.scheme == 'http' and settings.APP_ENV != 'production':
        return
    raise ImproperlyConfigured(f'URL identity provider harus HTTPS di production: {url}')


def _fetch_json(url: str, timeout: float) -> dict:
    _assert_safe_url(url)
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (skema divalidasi)
        if resp.status != 200:
            raise TokenValidationError('Identity provider tidak dapat dihubungi.')
        return json.loads(resp.read().decode('utf-8'))


class JWKSCache:
    """Cache JWKS thread-safe dengan TTL dan refetch terbatas saat kid tidak dikenal."""

    MIN_REFRESH_INTERVAL = 30  # detik

    def __init__(self):
        self._lock = threading.Lock()
        self._keys: KeySet | None = None
        self._kids: set[str] = set()
        self._fetched_at = 0.0
        self._jwks_uri: str | None = None

    def clear(self) -> None:
        with self._lock:
            self._keys = None
            self._kids = set()
            self._fetched_at = 0.0
            self._jwks_uri = None

    def _resolve_jwks_uri(self, cfg: OIDCSettings) -> str:
        if cfg.jwks_url:
            return cfg.jwks_url
        if self._jwks_uri:
            return self._jwks_uri
        metadata = _fetch_json(cfg.discovery_url, cfg.http_timeout)
        if (metadata.get('issuer') or '').rstrip('/') != cfg.issuer:
            raise ImproperlyConfigured('Issuer pada discovery document tidak sesuai OIDC_ISSUER.')
        jwks_uri = metadata.get('jwks_uri')
        if not jwks_uri:
            raise ImproperlyConfigured('Discovery document tidak memiliki jwks_uri.')
        self._jwks_uri = jwks_uri
        return jwks_uri

    def _refresh(self, cfg: OIDCSettings) -> None:
        data = _fetch_json(self._resolve_jwks_uri(cfg), cfg.http_timeout)
        # Hanya kunci penandatangan dengan algoritma yang diizinkan.
        keys = [
            k for k in data.get('keys', [])
            if k.get('use', 'sig') == 'sig' and (not k.get('alg') or k.get('alg') in cfg.algorithms)
        ]
        self._keys = KeySet.import_key_set({'keys': keys})
        self._kids = {k.get('kid') for k in keys if k.get('kid')}
        self._fetched_at = time.monotonic()

    def get(self, cfg: OIDCSettings, kid: str | None) -> KeySet:
        with self._lock:
            now = time.monotonic()
            expired = self._keys is None or (now - self._fetched_at) > cfg.jwks_cache_ttl
            unknown_kid = kid is not None and kid not in self._kids
            can_refetch = (now - self._fetched_at) > self.MIN_REFRESH_INTERVAL
            if expired or (unknown_kid and can_refetch):
                try:
                    self._refresh(cfg)
                except (TokenValidationError, ImproperlyConfigured):
                    raise
                except Exception as exc:  # jaringan / JSON rusak
                    logger.error('Gagal mengambil JWKS dari identity provider: %s', exc)
                    if self._keys is None:
                        raise TokenValidationError('Identity provider tidak dapat dihubungi.') from exc
            if kid is not None and kid not in self._kids:
                raise TokenValidationError('Kunci penandatangan token tidak dikenal.')
            return self._keys


jwks_cache = JWKSCache()


def _peek_header(token: str) -> dict:
    try:
        header_b64 = token.split('.')[0]
        header_b64 += '=' * (-len(header_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(header_b64))
    except Exception as exc:
        raise TokenValidationError('Format token tidak valid.') from exc


def validate_access_token(token: str, cfg: OIDCSettings | None = None) -> dict:
    """Validasi penuh access token JWT. Kembalikan klaim bila valid."""
    cfg = cfg or OIDCSettings.from_django()

    if token.count('.') != 2:
        raise TokenValidationError('Format token tidak valid.')
    header = _peek_header(token)
    alg = header.get('alg')
    if alg not in cfg.algorithms:
        raise TokenValidationError('Algoritma token tidak diizinkan.')

    key_set = jwks_cache.get(cfg, header.get('kid'))
    try:
        decoded = jwt.decode(token, key_set, algorithms=list(cfg.algorithms))
    except JoseError as exc:
        raise TokenValidationError('Signature token tidak valid.') from exc

    claims = decoded.claims
    if claims.get('iss') != cfg.issuer:
        raise TokenValidationError('Issuer token tidak valid.')

    registry = JWTClaimsRegistry(
        leeway=cfg.leeway,
        sub={'essential': True},
        exp={'essential': True},
        iat={'essential': True},
    )
    try:
        registry.validate(claims)
    except ExpiredTokenError as exc:
        raise TokenValidationError('Token telah kedaluwarsa.') from exc
    except JoseError as exc:
        raise TokenValidationError('Klaim token tidak valid.') from exc

    aud = claims.get('aud')
    audiences = aud if isinstance(aud, list) else [aud] if aud else []
    if cfg.audience not in audiences:
        raise TokenValidationError('Audience token tidak valid.')

    # Tolak ID token / refresh token yang dipakai sebagai access token (Keycloak: typ).
    token_typ = claims.get('typ')
    if token_typ is not None and str(token_typ).lower() not in ('bearer', 'at+jwt'):
        raise TokenValidationError('Jenis token bukan access token.')

    if cfg.allowed_azp:
        if claims.get('azp') not in cfg.allowed_azp:
            raise TokenValidationError('Client (azp) token tidak diizinkan.')

    return dict(claims)


def _claim_at_path(claims: dict, path: str):
    node = claims
    for part in path.split('.'):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def extract_app_roles(claims: dict, cfg: OIDCSettings | None = None) -> set[str]:
    """Petakan klaim role IdP ke empat peran aplikasi. Role lain diabaikan."""
    cfg = cfg or OIDCSettings.from_django()
    found: set[str] = set()
    for path in cfg.role_claim_paths:
        value = _claim_at_path(claims, path)
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            for idp_role in value:
                if not isinstance(idp_role, str):
                    continue
                app_role = cfg.role_mapping.get(idp_role)
                if app_role in ALL_ROLES:
                    found.add(app_role)
    return found
