from django.db import migrations, models


def set_existing_items_published(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Task = apps.get_model("projects", "Task")
    Project.objects.all().update(hidden=False)
    Task.objects.all().update(hidden=False)


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0005_fill_fake_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="task",
            name="hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_existing_items_published, migrations.RunPython.noop),
    ]
