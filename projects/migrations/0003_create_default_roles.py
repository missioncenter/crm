from django.db import migrations


PROTECTED_ROLE_NAMES = [
    "admin",
    "executor",
    "content",
    "guest",
    "auditor",
    "pm",
]


def create_default_roles(apps, schema_editor):
    Role = apps.get_model("projects", "Role")
    for role_name in PROTECTED_ROLE_NAMES:
        Role.objects.get_or_create(name=role_name, defaults={"description": f"System role {role_name}."})


def reverse_default_roles(apps, schema_editor):
    # Do not delete protected roles on rollback to avoid accidental data loss.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0002_role"),
    ]

    operations = [
        migrations.RunPython(create_default_roles, reverse_default_roles),
    ]
