import random
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


USER_PROFILES = [
    ("alice", "Alice", "Johnson", "alice@example.com"),
    ("bob", "Bob", "Petrov", "bob@example.com"),
    ("carol", "Carol", "Sidorova", "carol@example.com"),
    ("dave", "Dave", "Ivanov", "dave@example.com"),
    ("eva", "Eva", "Smirnova", "eva@example.com"),
    ("frank", "Frank", "Kuznetsov", "frank@example.com"),
    ("grace", "Grace", "Volkova", "grace@example.com"),
    ("henry", "Henry", "Morozov", "henry@example.com"),
]

GROUP_NAMES = ["Admins", "Managers", "Developers", "Support", "Guests"]
PROJECT_TITLES = [
    "Customer Portal Redesign",
    "Internal CRM Upgrade",
    "Marketing Campaign Launch",
    "Onboarding Automation",
    "Mobile App Release",
]
TASK_SUBJECTS = [
    "Design dashboard widgets",
    "Implement task filtering",
    "Setup notification emails",
    "Migrate legacy data",
    "Create user onboarding flow",
    "Validate form input",
    "Configure access rights",
    "Optimize search queries",
    "Write API documentation",
    "Prepare release notes",
    "Review pull requests",
    "Fix mobile layout bugs",
    "Add calendar integration",
    "Improve page load time",
    "Update user roles matrix",
    "Test authentication flow",
    "Refactor task model",
    "Create analytics reports",
    "Implement drag-and-drop board",
    "Add audit logging",
]

STATUS_CHOICES = ["ToDo", "InProgress", "Review", "Done"]


def create_fake_data(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Group = apps.get_model("auth", "Group")
    Role = apps.get_model("projects", "Role")
    Project = apps.get_model("projects", "Project")
    Task = apps.get_model("projects", "Task")

    random.seed(42)

    groups = {}
    for group_name in GROUP_NAMES:
        group, _ = Group.objects.get_or_create(name=group_name)
        groups[group_name] = group

    roles = {}
    for role_name in ["admin", "executor", "content", "auditor", "pm", "guest"]:
        role, _ = Role.objects.get_or_create(
            name=role_name,
            defaults={"description": f"System role {role_name}."},
        )
        roles[role_name] = role

    created_users = []
    for i, (username, first_name, last_name, email) in enumerate(USER_PROFILES, start=1):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": make_password("password"),
                "is_staff": username in ("alice", "bob", "carol"),
                "is_superuser": False,
            },
        )
        if created:
            user.save()
        created_users.append(user)

    admin_user = User.objects.filter(username="admin").first()
    if admin_user:
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        roles["admin"].users.add(admin_user)
        groups["Admins"].user_set.add(admin_user)

    for index, user in enumerate(created_users):
        if index % 2 == 0:
            groups["Developers"].user_set.add(user)
        else:
            groups["Support"].user_set.add(user)

        if index < 3:
            roles["executor"].users.add(user)
        if index == 2:
            roles["pm"].users.add(user)
        if index == 4:
            roles["content"].users.add(user)

    projects = []
    for idx, title in enumerate(PROJECT_TITLES, start=1):
        owner = random.choice(created_users)
        project, _ = Project.objects.get_or_create(
            title=title,
            defaults={
                "description": f"Project {title} for CRM Local MVP.",
                "owner": owner,
            },
        )
        if not project.members.exists():
            members = random.sample(created_users, min(4, len(created_users)))
            project.members.set(members)
            if owner not in project.members.all():
                project.members.add(owner)
        projects.append(project)

    today = date.today()
    for idx, subject in enumerate(TASK_SUBJECTS, start=1):
        project = random.choice(projects)
        executor_candidates = list(project.members.all())
        executor = random.choice(executor_candidates) if executor_candidates else None
        task_title = subject
        status = random.choice(STATUS_CHOICES)
        deadline = today + timedelta(days=random.randint(-10, 30))
        task, created = Task.objects.get_or_create(
            title=task_title,
            project=project,
            defaults={
                "description": f"{task_title} for project {project.title}.",
                "status": status,
                "executor": executor,
                "deadline": deadline,
            },
        )
        if created:
            co_executors = [u for u in executor_candidates if u != executor]
            for co in random.sample(co_executors, min(2, len(co_executors))):
                task.co_executors.add(co)


def reverse_fill_fake_data(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Group = apps.get_model("auth", "Group")
    Role = apps.get_model("projects", "Role")
    Project = apps.get_model("projects", "Project")
    Task = apps.get_model("projects", "Task")

    for username, *_ in USER_PROFILES:
        User.objects.filter(username=username).delete()

    Task.objects.filter(title__in=TASK_SUBJECTS).delete()
    Project.objects.filter(title__in=PROJECT_TITLES).delete()

    for group_name in GROUP_NAMES:
        Group.objects.filter(name=group_name).delete()

    for role_name in ["executor", "content", "auditor", "pm", "guest"]:
        Role.objects.filter(name=role_name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0004_create_default_admin"),
    ]

    operations = [
        migrations.RunPython(create_fake_data, reverse_fill_fake_data),
    ]
