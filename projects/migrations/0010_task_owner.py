from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0009_task_progress"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_tasks",
                to="auth.user",
            ),
        ),
    ]