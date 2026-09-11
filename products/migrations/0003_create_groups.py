from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ['admin', 'sales', 'hr']:
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['admin', 'sales', 'hr']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_crm_deal_value_crm_next_follow_up_crm_status_and_more'),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]