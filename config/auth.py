import os
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import authentication, exceptions
from joserfc import jwt
from joserfc.errors import BadSignatureError, ExpiredTokenError


class OIDCAuthentication(authentication.BaseAuthentication):
    """
    Enterprise Authentication supporting:
    1. Fast Demo Bearer Tokens (Strictly in non-production environments when DEMO_MODE=True)
    2. OpenID Connect (OIDC) JWT Bearer Tokens with issuer/sub claim verification
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]
        User = get_user_model()

        # 1. Demo Mode Fast Token Authentication
        if getattr(settings, 'DEMO_MODE', False) and getattr(settings, 'APP_ENV', 'development') != 'production':
            if token.startswith('demo-'):
                username = token.replace('demo-', '').strip()
                try:
                    user = User.objects.get(username=username)
                    if not user.is_active:
                        raise exceptions.AuthenticationFailed("Akun pengguna demo telah dinonaktifkan.")
                    return (user, None)
                except User.DoesNotExist:
                    raise exceptions.AuthenticationFailed(f"Demo user '{username}' tidak ditemukan di database.")

        # 2. Production OIDC JWT Validation
        try:
            oidc_config = getattr(settings, 'AUTHLIB_OAUTH_CLIENTS', {}).get('oidc_provider', {})
            client_secret = oidc_config.get('client_secret', settings.SECRET_KEY)
            expected_issuer = oidc_config.get('issuer')
            expected_audience = oidc_config.get('client_id')

            token_obj = jwt.decode(token, client_secret)
            claims = token_obj.claims

            # Check expiration
            if 'exp' in claims and claims.is_expired():
                raise exceptions.AuthenticationFailed("OIDC Token telah kedaluwarsa.")

            # Check issuer if configured
            issuer = claims.get('iss')
            if expected_issuer and issuer != expected_issuer:
                raise exceptions.AuthenticationFailed("OIDC Token issuer tidak cocok.")

            # Check audience if configured
            aud = claims.get('aud')
            if expected_audience and aud != expected_audience:
                raise exceptions.AuthenticationFailed("OIDC Token audience tidak cocok.")

            sub = claims.get('sub')
            username = claims.get('preferred_username') or claims.get('email') or sub
            email = claims.get('email', '')

            if not username:
                raise exceptions.AuthenticationFailed("OIDC Token tidak memiliki klaim identitas (sub/username).")

            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'oidc_issuer': issuer or '',
                    'oidc_subject': sub or ''
                }
            )

            if not user.is_active:
                raise exceptions.AuthenticationFailed("Akun pengguna telah dinonaktifkan.")

            return (user, None)

        except (BadSignatureError, ExpiredTokenError) as e:
            raise exceptions.AuthenticationFailed(f"Token OIDC tidak valid: {str(e)}")
        except Exception as e:
            raise exceptions.AuthenticationFailed("Token otorisasi Bearer tidak valid atau rusak.")

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
