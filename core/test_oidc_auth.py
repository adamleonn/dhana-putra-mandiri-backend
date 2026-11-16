"""
Tes autentikasi OAuth 2.0 / OIDC (JWT access token) dan RBAC per endpoint.

JWKS identity provider disimulasikan: kunci RSA dibuat saat tes dan
`config.oidc._fetch_json` di-patch agar mengembalikan discovery document &
JWKS palsu, sehingga tes tidak memerlukan Keycloak berjalan.
"""

import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from joserfc import jwt
from joserfc.jwk import KeySet, OctKey, RSAKey
from rest_framework.test import APIClient

from config.oidc import jwks_cache

User = get_user_model()

ISSUER = 'http://idp.test/realms/dhana-putra'
AUDIENCE = 'dhana-putra-api'
CLIENT_ID = 'dhana-putra-web'
KID = 'test-key-1'

OIDC_TEST_SETTINGS = dict(
    OIDC_ISSUER=ISSUER,
    OIDC_DISCOVERY_URL='',
    OIDC_JWKS_URL='',
    OIDC_API_AUDIENCE=AUDIENCE,
    OIDC_ALLOWED_ALGORITHMS=['RS256'],
    OIDC_ALLOWED_CLIENT_IDS=[CLIENT_ID],
    OIDC_ROLE_CLAIM_PATHS=[f'resource_access.{AUDIENCE}.roles'],
    OIDC_ROLE_MAPPING={'direktur': 'direktur', 'admin': 'admin', 'gudang': 'gudang', 'stakeholder': 'stakeholder'},
    OIDC_LEEWAY_SECONDS=0,
    OIDC_JWKS_CACHE_SECONDS=300,
    OIDC_HTTP_TIMEOUT_SECONDS=1,
    OIDC_LINK_EXISTING_BY_USERNAME=True,
    OIDC_AUTO_CREATE_USERS=True,
)


class OIDCTestMixin:
    signing_key: RSAKey
    other_key: RSAKey

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.signing_key = RSAKey.generate_key(2048, parameters={'kid': KID, 'use': 'sig', 'alg': 'RS256'})
        cls.other_key = RSAKey.generate_key(2048, parameters={'kid': KID, 'use': 'sig', 'alg': 'RS256'})
        cls.jwks = KeySet([cls.signing_key]).as_dict(private=False)

    def setUp(self):
        super().setUp()
        jwks_cache.clear()
        self.fetch_calls = []

        def fake_fetch(url, timeout):
            self.fetch_calls.append(url)
            if url.endswith('/.well-known/openid-configuration'):
                return {'issuer': ISSUER, 'jwks_uri': f'{ISSUER}/protocol/openid-connect/certs'}
            if url.endswith('/certs'):
                return self.jwks
            raise AssertionError(f'URL tak terduga: {url}')

        patcher = mock.patch('config.oidc._fetch_json', side_effect=fake_fetch)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient()

    def make_token(self, *, roles=('direktur',), sub=None, username='direktur', key=None, kid=KID,
                   alg='RS256', **overrides):
        now = int(time.time())
        claims = {
            'iss': ISSUER,
            'aud': [AUDIENCE, 'account'],
            'sub': sub or f'sub-{username}',
            'azp': CLIENT_ID,
            'typ': 'Bearer',
            'iat': now,
            'nbf': now,
            'exp': now + 300,
            'preferred_username': username,
            'email': f'{username}@example.test',
            'given_name': username.title(),
            'family_name': 'Test',
            'resource_access': {AUDIENCE: {'roles': list(roles)}},
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        header = {'alg': alg, 'kid': kid} if kid else {'alg': alg}
        return jwt.encode(header, claims, key or self.signing_key)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


@override_settings(**OIDC_TEST_SETTINGS)
class OIDCTokenValidationTests(OIDCTestMixin, TestCase):
    def test_valid_token_authenticates_and_returns_profile(self):
        self.auth(self.make_token(roles=['direktur'], username='budi'))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data['username'], 'budi')
        self.assertEqual(res.data['roles'], ['direktur'])
        self.assertEqual(res.data['primary_role'], 'direktur')
        user = User.objects.get(username='budi')
        self.assertEqual(user.oidc_issuer, ISSUER)
        self.assertEqual(user.oidc_subject, 'sub-budi')
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.groups.filter(name='Direktur').exists())

    def test_missing_token_is_rejected(self):
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 401)
        self.assertIn('Bearer', res.get('WWW-Authenticate', ''))

    def test_legacy_demo_token_is_rejected(self):
        User.objects.create_user(username='direktur').groups.add(Group.objects.create(name='Direktur'))
        for token in ('demo-direktur', 'demo-admin', 'demo-gudang', 'demo-stakeholder'):
            self.auth(token)
            res = self.client.get('/api/inventory/products/')
            self.assertEqual(res.status_code, 401, token)

    def test_expired_token_is_rejected(self):
        past = int(time.time()) - 3600
        self.auth(self.make_token(iat=past - 300, nbf=past - 300, exp=past))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 401)
        self.assertIn('kedaluwarsa', str(res.data))

    def test_not_yet_valid_token_is_rejected(self):
        future = int(time.time()) + 3600
        self.auth(self.make_token(nbf=future, exp=future + 300))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_wrong_issuer_is_rejected(self):
        self.auth(self.make_token(iss='http://evil.test/realms/dhana-putra'))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 401)
        self.assertIn('Issuer', str(res.data))

    def test_wrong_audience_is_rejected(self):
        self.auth(self.make_token(aud=['account', 'other-api']))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 401)
        self.assertIn('Audience', str(res.data))

    def test_missing_audience_is_rejected(self):
        self.auth(self.make_token(aud=None))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_disallowed_client_azp_is_rejected(self):
        self.auth(self.make_token(azp='rogue-client'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_id_token_cannot_be_used_as_access_token(self):
        self.auth(self.make_token(typ='ID'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_token_signed_by_unknown_key_is_rejected(self):
        self.auth(self.make_token(key=self.other_key))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 401)
        self.assertIn('Signature', str(res.data))

    def test_unknown_kid_is_rejected_and_refetch_is_rate_limited(self):
        self.auth(self.make_token(kid='rotated-key'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)
        jwks_fetches = [u for u in self.fetch_calls if u.endswith('/certs')]
        self.assertEqual(len(jwks_fetches), 1, 'JWKS tidak boleh di-fetch berulang oleh token palsu')

    def test_hs256_token_signed_with_public_key_material_is_rejected(self):
        # Serangan "algorithm confusion": HS256 memakai modulus publik sebagai secret.
        fake_secret = OctKey.import_key(self.signing_key.as_dict(private=False)['n'])
        token = jwt.encode({'alg': 'HS256', 'kid': KID}, {
            'iss': ISSUER, 'aud': AUDIENCE, 'sub': 'x', 'exp': int(time.time()) + 60, 'iat': int(time.time()),
        }, fake_secret)
        self.auth(token)
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_unsigned_alg_none_token_is_rejected(self):
        import base64, json
        def b64(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
        token = f"{b64({'alg': 'none'})}.{b64({'iss': ISSUER, 'aud': AUDIENCE, 'sub': 'x', 'exp': 9999999999})}."
        self.auth(token)
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_malformed_token_is_rejected(self):
        self.auth('not-a-jwt')
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_jwks_is_cached_between_requests(self):
        token = self.make_token()
        self.auth(token)
        for _ in range(3):
            self.assertEqual(self.client.get('/api/core/me/').status_code, 200)
        self.assertEqual(len([u for u in self.fetch_calls if u.endswith('/certs')]), 1)


@override_settings(**OIDC_TEST_SETTINGS)
class OIDCUserAndRoleMappingTests(OIDCTestMixin, TestCase):
    def test_user_without_role_is_forbidden_everywhere(self):
        self.auth(self.make_token(roles=[], username='tanpa-peran'))
        for url in ('/api/core/me/', '/api/inventory/products/', '/api/finance/reports/sales-trends/'):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, url)
        self.assertIn('belum memiliki peran', str(self.client.get('/api/core/me/').data))

    def test_unknown_idp_roles_are_ignored(self):
        self.auth(self.make_token(roles=['offline_access', 'superuser', 'Sales', 'Accounting'], username='x'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 403)

    def test_realm_roles_are_not_trusted_by_default(self):
        self.auth(self.make_token(roles=[], username='y', realm_access={'roles': ['direktur']}))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 403)

    def test_existing_user_is_linked_by_username_and_keeps_data(self):
        legacy = User.objects.create_user(username='gudang', password='old-local-pass')
        legacy.groups.add(Group.objects.create(name='Gudang'))
        self.auth(self.make_token(roles=['gudang'], username='gudang', sub='kc-uuid-gudang'))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['id'], legacy.pk)
        legacy.refresh_from_db()
        self.assertEqual(legacy.oidc_subject, 'kc-uuid-gudang')
        self.assertEqual(User.objects.filter(username='gudang').count(), 1)

    def test_username_takeover_by_different_subject_is_rejected(self):
        User.objects.create_user(username='admin', oidc_issuer=ISSUER, oidc_subject='original-sub')
        self.auth(self.make_token(roles=['direktur'], username='admin', sub='attacker-sub'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)

    def test_roles_are_synced_from_token_on_every_request(self):
        self.auth(self.make_token(roles=['direktur', 'admin'], username='rina'))
        self.assertEqual(self.client.get('/api/core/me/').data['roles'], ['admin', 'direktur'])
        self.auth(self.make_token(roles=['stakeholder'], username='rina'))
        res = self.client.get('/api/core/me/')
        self.assertEqual(res.data['roles'], ['stakeholder'])
        user = User.objects.get(username='rina')
        self.assertEqual(sorted(user.groups.values_list('name', flat=True)), ['Stakeholder'])
        # Peran dicabut di IdP -> akses hilang
        self.auth(self.make_token(roles=[], username='rina'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 403)

    def test_local_superuser_flag_does_not_bypass_idp_roles(self):
        User.objects.create_superuser(username='root', password='x', email='r@example.test')
        self.auth(self.make_token(roles=['gudang'], username='root'))
        self.assertEqual(self.client.get('/api/finance/reports/sales-trends/').status_code, 403)

    def test_inactive_user_is_rejected(self):
        User.objects.create_user(username='nonaktif', is_active=False)
        self.auth(self.make_token(roles=['direktur'], username='nonaktif'))
        self.assertEqual(self.client.get('/api/core/me/').status_code, 401)


D, A, G, S = 'direktur', 'admin', 'gudang', 'stakeholder'
ALL = {D, A, G, S}

# (method, url, peran yang diizinkan)
ENDPOINT_MATRIX = [
    ('get', '/api/core/me/', ALL),
    ('get', '/api/core/customers/', ALL),
    ('post', '/api/core/customers/', {D, A}),
    ('get', '/api/core/suppliers/', ALL),
    ('post', '/api/core/suppliers/', {D, A}),
    ('get', '/api/core/audit-logs/', {D}),
    ('get', '/api/finance/customers/', ALL),
    ('post', '/api/finance/suppliers/', {D, A}),
    ('get', '/api/inventory/products/', ALL),
    ('post', '/api/inventory/products/', {D, A}),
    ('get', '/api/inventory/products/stock-estimation/', ALL),
    ('get', '/api/inventory/purchase-orders/', ALL),
    ('post', '/api/inventory/purchase-orders/', {D, A}),
    ('get', '/api/inventory/goods-receipts/', ALL),
    ('post', '/api/inventory/goods-receipts/', {D, A}),
    ('post', '/api/inventory/goods-receipts/999999/confirm/', {D, G}),
    ('get', '/api/inventory/deliveries/', ALL),
    ('post', '/api/inventory/deliveries/', {D, A, G}),
    ('post', '/api/inventory/deliveries/999999/confirm/', {D, G}),
    ('delete', '/api/inventory/deliveries/999999/', {D, A}),
    ('get', '/api/inventory/stock-movements/', ALL),
    ('post', '/api/inventory/stock-movements/', set()),
    ('get', '/api/finance/chart-of-accounts/', {D, A, S}),
    ('post', '/api/finance/chart-of-accounts/', {D}),
    ('get', '/api/finance/accounting-periods/', {D, A, S}),
    ('post', '/api/finance/accounting-periods/', {D}),
    ('post', '/api/finance/accounting-periods/999999/close_period/', {D}),
    ('post', '/api/finance/accounting-periods/999999/reopen_period/', {D}),
    ('get', '/api/finance/general-ledger/', {D, S}),
    ('get', '/api/finance/sales-invoices/', {D, A, S}),
    ('post', '/api/finance/sales-invoices/', {D, A}),
    ('post', '/api/finance/sales-invoices/999999/revise/', {D}),
    ('get', '/api/finance/debit-notes/', {D, A, S}),
    ('post', '/api/finance/debit-notes/', {D}),
    ('get', '/api/finance/payments/', {D, A, S}),
    ('post', '/api/finance/payments/', {D, A}),
    ('get', '/api/finance/reports/balance-sheet/', {D, A, S}),
    ('get', '/api/finance/reports/product-sales/', {D, A, S}),
    ('get', '/api/finance/reports/sales-trends/', {D, A, S}),
    ('get', '/api/finance/reports/annual-report/', {D, A, S}),
    ('get', '/api/finance/reports/pie-charts/', {D, A, S}),
    ('get', '/api/hr/employees/', {D, A, S}),
    ('post', '/api/hr/employees/', {D, A}),
    ('get', '/api/hr/mutations/', {D, A, S}),
    ('post', '/api/hr/mutations/', {D, A}),
    ('get', '/api/hr/labor-records/', ALL),
    ('post', '/api/hr/labor-records/', {D, A, G}),
    ('get', '/api/hr/payroll-slips/', {D, A, S}),
    ('post', '/api/hr/payroll-slips/generate/', {D}),
    ('post', '/api/hr/payroll-slips/999999/approve/', {D}),
]


@override_settings(**OIDC_TEST_SETTINGS)
class RoleEndpointMatrixTests(OIDCTestMixin, TestCase):
    """Setiap peran diuji terhadap setiap endpoint: diizinkan != 401/403, ditolak == 403."""

    def test_endpoint_access_per_role(self):
        tokens = {role: self.make_token(roles=[role], username=f'user-{role}') for role in ALL}
        for method, url, allowed in ENDPOINT_MATRIX:
            for role in sorted(ALL):
                with self.subTest(role=role, method=method, url=url):
                    self.auth(tokens[role])
                    res = getattr(self.client, method)(url, {}, format='json')
                    if role in allowed:
                        self.assertNotIn(res.status_code, (401, 403),
                                         f'{role} seharusnya boleh {method.upper()} {url}: {res.content[:200]}')
                        self.assertLess(res.status_code, 500, res.content[:300])
                    else:
                        self.assertEqual(res.status_code, 403,
                                         f'{role} seharusnya DITOLAK {method.upper()} {url}')

    def test_sales_trends_report_per_role(self):
        expected = {D: 200, A: 200, S: 200, G: 403}
        for role, code in expected.items():
            with self.subTest(role=role):
                self.auth(self.make_token(roles=[role], username=f'trend-{role}'))
                res = self.client.get('/api/finance/reports/sales-trends/', {'year': 2026})
                self.assertEqual(res.status_code, code, res.content[:200])
                if code == 200:
                    self.assertEqual(res.data['year'], 2026)
                    self.assertIn('trends', res.data)

    def test_stakeholder_cannot_write_anything(self):
        self.auth(self.make_token(roles=[S], username='stk'))
        for method, url, _ in ENDPOINT_MATRIX:
            if method == 'get':
                continue
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 403)
