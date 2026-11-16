"""
Migrasi pengguna lama ke Keycloak.

Menghasilkan berkas JSON "Partial Import" Keycloak berisi pengguna aktif yang
memiliki salah satu dari empat peran aplikasi, lengkap dengan client role
pada client API. Password TIDAK diekspor: pengguna diberi required action
UPDATE_PASSWORD (atau set password lewat skrip dev) saat login pertama.

Contoh:
    python manage.py export_keycloak_users --output keycloak/users-import.json
"""

import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.roles import GROUP_TO_ROLE, ROLE_TO_GROUP


class Command(BaseCommand):
    help = 'Ekspor pengguna & peran ke format Partial Import Keycloak (tanpa password).'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='-', help="Path berkas JSON, '-' untuk stdout")
        parser.add_argument('--client-id', default=settings.OIDC_API_AUDIENCE,
                            help='Client Keycloak pemilik client role (default: OIDC_API_AUDIENCE)')
        parser.add_argument('--no-required-action', action='store_true',
                            help='Jangan tambahkan required action UPDATE_PASSWORD')

    def handle(self, *args, **opts):
        User = get_user_model()
        users = (
            User.objects.filter(is_active=True, groups__name__in=ROLE_TO_GROUP.values())
            .distinct().prefetch_related('groups').order_by('username')
        )
        exported = []
        for user in users:
            roles = sorted({GROUP_TO_ROLE[g.name] for g in user.groups.all() if g.name in GROUP_TO_ROLE})
            entry = {
                'username': user.username,
                'enabled': True,
                'email': user.email or None,
                'emailVerified': bool(user.email),
                'firstName': user.first_name or user.username,
                'lastName': user.last_name or '-',
                'clientRoles': {opts['client_id']: roles},
                'requiredActions': [] if opts['no_required_action'] else ['UPDATE_PASSWORD'],
            }
            exported.append({k: v for k, v in entry.items() if v is not None})

        payload = json.dumps({'ifResourceExists': 'SKIP', 'users': exported}, indent=2, ensure_ascii=False)
        if opts['output'] == '-':
            self.stdout.write(payload)
        else:
            with open(opts['output'], 'w', encoding='utf-8') as fh:
                fh.write(payload + '\n')
            self.stderr.write(self.style.SUCCESS(f'{len(exported)} pengguna diekspor ke {opts["output"]}'))
