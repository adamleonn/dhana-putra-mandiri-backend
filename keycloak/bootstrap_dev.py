"""
Bootstrap Keycloak untuk pengembangan lokal (stdlib only, tanpa dependensi).

Fungsi:
  1. Set password pengguna dev realm `dhana-putra` dari environment variable
     (password TIDAK disimpan di source code / realm JSON).
  2. (Opsional) Tulis client secret `dhana-putra-web` ke berkas .env.local
     frontend, tanpa menampilkannya di terminal.

Environment variable:
  KEYCLOAK_URL               default http://localhost:8080
  KEYCLOAK_ADMIN             username admin master realm
  KEYCLOAK_ADMIN_PASSWORD    password admin master realm
  KC_DEV_USER_PASSWORD       password untuk semua user dev (direktur, admin, gudang,
                             stakeholder, tanpa-peran). Bisa juga per user:
                             KC_DEV_PASSWORD_DIREKTUR, KC_DEV_PASSWORD_ADMIN, ...

Contoh:
  python keycloak/bootstrap_dev.py --set-passwords --write-client-secret ../frontend/.env.local
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REALM = 'dhana-putra'
WEB_CLIENT = 'dhana-putra-web'
DEV_USERS = ['direktur', 'admin', 'gudang', 'stakeholder', 'tanpa-peran']


def _request(method: str, url: str, token: str | None = None, data=None, form: bool = False):
    headers = {'Accept': 'application/json'}
    body = None
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (URL dari konfigurasi lokal)
        raw = resp.read()
        return json.loads(raw) if raw else None


def admin_token(base: str) -> str:
    user = os.environ.get('KEYCLOAK_ADMIN')
    password = os.environ.get('KEYCLOAK_ADMIN_PASSWORD')
    if not user or not password:
        sys.exit('KEYCLOAK_ADMIN dan KEYCLOAK_ADMIN_PASSWORD wajib diset.')
    data = _request('POST', f'{base}/realms/master/protocol/openid-connect/token', data={
        'grant_type': 'password', 'client_id': 'admin-cli', 'username': user, 'password': password,
    }, form=True)
    return data['access_token']


def set_passwords(base: str, token: str) -> None:
    default = os.environ.get('KC_DEV_USER_PASSWORD')
    for username in DEV_USERS:
        password = os.environ.get(f'KC_DEV_PASSWORD_{username.upper().replace("-", "_")}', default)
        if not password:
            sys.exit(f'Password untuk {username} tidak diset (KC_DEV_USER_PASSWORD).')
        users = _request('GET', f'{base}/admin/realms/{REALM}/users?exact=true&username={username}', token)
        if not users:
            print(f'  [skip] user {username} tidak ditemukan')
            continue
        _request('PUT', f'{base}/admin/realms/{REALM}/users/{users[0]["id"]}/reset-password', token,
                 {'type': 'password', 'value': password, 'temporary': False})
        print(f'  [ok] password {username} diset')


def write_client_secret(base: str, token: str, env_path: str) -> None:
    clients = _request('GET', f'{base}/admin/realms/{REALM}/clients?clientId={WEB_CLIENT}', token)
    if not clients:
        sys.exit(f'Client {WEB_CLIENT} tidak ditemukan.')
    secret = _request('GET', f'{base}/admin/realms/{REALM}/clients/{clients[0]["id"]}/client-secret', token)['value']
    content = ''
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as fh:
            content = fh.read()
    line = f'OIDC_CLIENT_SECRET={secret}'
    if re.search(r'^OIDC_CLIENT_SECRET=.*$', content, flags=re.M):
        content = re.sub(r'^OIDC_CLIENT_SECRET=.*$', line, content, flags=re.M)
    else:
        content = content.rstrip('\n') + ('\n' if content else '') + line + '\n'
    with open(env_path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print(f'  [ok] OIDC_CLIENT_SECRET ditulis ke {env_path} (tidak ditampilkan)')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--set-passwords', action='store_true')
    parser.add_argument('--write-client-secret', metavar='ENV_FILE')
    args = parser.parse_args()
    base = os.environ.get('KEYCLOAK_URL', 'http://localhost:8080').rstrip('/')
    token = admin_token(base)
    if args.set_passwords:
        set_passwords(base, token)
    if args.write_client_secret:
        write_client_secret(base, token, args.write_client_secret)


if __name__ == '__main__':
    main()
