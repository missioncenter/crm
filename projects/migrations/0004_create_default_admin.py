from django.conf import settings
from django.db import migrations


def create_default_admin(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Role = apps.get_model("projects", "Role")

    admin_role, _ = Role.objects.get_or_create(
        name="admin",
        defaults={"description": "System role admin."},
    )

    if not User.objects.filter(username="admin").exists():
        email = "admin@example.com"
        User.objects.create_superuser(username="admin", email=email, password="admin")
        admin_user = User.objects.get(username="admin")
        admin_role.users.add(admin_user)


def reverse_default_admin(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    admin_user = User.objects.filter(username="admin").first()
    if admin_user:
        admin_user.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0003_create_default_roles"),
    ]

    operations = [
        migrations.RunPython(create_default_admin, reverse_default_admin),
    ]
