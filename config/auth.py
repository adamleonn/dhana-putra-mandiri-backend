import os
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import authentication, exceptions
from joserfc import jwt
from joserfc.errors import BadSignatureError, ExpiredTokenError

User = get_user_model()


class OIDCAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]

        if settings.DEMO_MODE or settings.APP_ENV == 'development':
            if token.startswith('demo-'):
                username = token.replace('demo-', '').strip()
                try:
                    user = User.objects.get(username=username)
                    return (user, None)
                except User.DoesNotExist:
                    raise exceptions.AuthenticationFailed(f"Demo user '{username}' does not exist.")

        try:
            secret_key = settings.AUTHLIB_OAUTH_CLIENTS.get('oidc_provider', {}).get('client_secret', settings.SECRET_KEY)
            token_obj = jwt.decode(token, secret_key)
            claims = token_obj.claims

            username = claims.get('preferred_username') or claims.get('sub')
            email = claims.get('email', '')

            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': email}
            )
            return (user, None)
        except (BadSignatureError, ExpiredTokenError) as e:
            raise exceptions.AuthenticationFailed(f"Invalid OIDC Token: {str(e)}")
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid or malformed OIDC Authorization token.")

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
