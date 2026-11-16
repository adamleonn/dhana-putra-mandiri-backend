from django.db import migrations


def retire_legacy_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('core', 'User')
    alias = schema_editor.connection.alias
    retired = Group.objects.using(alias).filter(name__in=['Sales', 'Finance', 'Accounting'])
    users = User.objects.using(alias)
    retained = users.filter(groups__name__in=['Stakeholder', 'Direktur', 'Admin', 'Gudang'])
    users.filter(groups__in=retired, is_superuser=False).exclude(pk__in=retained).update(is_active=False)
    retired.delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunPython(retire_legacy_roles)]
