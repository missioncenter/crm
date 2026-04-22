from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from .forms import GroupForm, ProjectForm, RoleForm, TaskForm, UserCreateForm, UserUpdateForm
from .models import Project, Role, Task, TaskStatus

User = get_user_model()


def has_role(user, role_name):
    if not user.is_authenticated:
        return False
    return user.roles.filter(name__iexact=role_name).exists() or user.is_superuser


def is_admin_role(user):
    return has_role(user, "admin")


def is_moderator_role(user):
    return has_role(user, "moderator")


def is_executor_role(user):
    return has_role(user, "executor")


def can_manage_projects(user):
    return is_admin_role(user) or is_moderator_role(user)


def can_manage_users(user):
    return is_admin_role(user)


@login_required
def dashboard(request):
    tasks = Task.objects.select_related("project", "executor").prefetch_related("co_executors")
    status_map = {status.value: status.label for status in TaskStatus}
    columns = [
        {
            "key": value,
            "label": label,
            "tasks": [task for task in tasks if task.status == value],
        }
        for value, label in status_map.items()
    ]

    projects_count = Project.objects.count()
    groups_count = Group.objects.count()
    users_count = User.objects.count()
    tasks_count = tasks.count()
    overdue_count = tasks.filter(deadline__lt=timezone.now().date()).exclude(status=TaskStatus.DONE).count()

    stats = [
        {"label": "Projects", "value": projects_count},
        {"label": "Groups", "value": groups_count},
        {"label": "Users", "value": users_count},
        {"label": "Tasks", "value": tasks_count},
        {"label": "Overdue", "value": overdue_count},
    ]

    return render(
        request,
        "projects/dashboard.html",
        {
            "columns": columns,
            "stats": stats,
        },
    )


@login_required
def project_list(request):
    projects = Project.objects.select_related("owner").prefetch_related("members")
    return render(request, "projects/project_list.html", {"projects": projects})


@login_required
def project_create(request):
    if not can_manage_projects(request.user):
        return HttpResponseForbidden("Only admins or moderators can create projects.")
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("project_list")
    return render(request, "projects/project_form.html", {"form": form, "form_title": "Create Project"})


@login_required
def project_update(request, pk):
    if not can_manage_projects(request.user):
        return HttpResponseForbidden("Only admins or moderators can edit projects.")
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=project)
    if form.is_valid():
        form.save()
        return redirect("project_list")
    return render(request, "projects/project_form.html", {"form": form, "form_title": f"Edit Project: {project.title}"})


@login_required
def project_delete(request, pk):
    if not can_manage_projects(request.user):
        return HttpResponseForbidden("Only admins or moderators can delete projects.")
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        project.delete()
        return redirect("project_list")
    return render(request, "projects/project_confirm_delete.html", {"project": project})


@login_required
def user_list(request):
    if not can_manage_users(request.user):
        return HttpResponseForbidden("Only admins can manage users.")
    users = User.objects.order_by("username").prefetch_related(
        "groups", "projects", "assigned_tasks", "supporting_tasks", "roles"
    )
    return render(request, "projects/user_list.html", {"users": users})


@login_required
def user_create(request):
    if not can_manage_users(request.user):
        return HttpResponseForbidden("Only admins can manage users.")
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "projects/user_form.html", {"form": form, "form_title": "Create User"})


@login_required
def user_update(request, pk):
    if not can_manage_users(request.user):
        return HttpResponseForbidden("Only admins can manage users.")
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "projects/user_form.html", {"form": form, "form_title": f"Edit User: {user.username}"})


@login_required
def user_delete(request, pk):
    if not can_manage_users(request.user):
        return HttpResponseForbidden("Only admins can manage users.")
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        user.delete()
        return redirect("user_list")
    return render(request, "projects/user_confirm_delete.html", {"user": user})


@login_required
def group_list(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only admins can manage groups.")
    groups = Group.objects.order_by("name")
    return render(request, "projects/group_list.html", {"groups": groups})


@login_required
def group_create(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only admins can manage groups.")
    form = GroupForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("group_list")
    return render(request, "projects/group_form.html", {"form": form, "form_title": "Create Group"})


@login_required
def group_update(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only admins can manage groups.")
    group = get_object_or_404(Group, pk=pk)
    form = GroupForm(request.POST or None, instance=group)
    if form.is_valid():
        form.save()
        return redirect("group_list")
    return render(request, "projects/group_form.html", {"form": form, "form_title": f"Edit Group: {group.name}"})


@login_required
def group_delete(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only admins can manage groups.")
    group = get_object_or_404(Group, pk=pk)
    if request.method == "POST":
        group.delete()
        return redirect("group_list")
    return render(request, "projects/group_confirm_delete.html", {"group": group})


@login_required
def role_list(request):
    if not is_admin_role(request.user):
        return HttpResponseForbidden("Only admins can manage roles.")
    roles = Role.objects.prefetch_related("users").order_by("name")
    return render(request, "projects/role_list.html", {"roles": roles})


@login_required
def role_create(request):
    if not is_admin_role(request.user):
        return HttpResponseForbidden("Only admins can manage roles.")
    form = RoleForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("role_list")
    return render(request, "projects/role_form.html", {"form": form, "form_title": "Create Role"})


@login_required
def role_update(request, pk):
    if not is_admin_role(request.user):
        return HttpResponseForbidden("Only admins can manage roles.")
    role = get_object_or_404(Role, pk=pk)
    form = RoleForm(request.POST or None, instance=role)
    if form.is_valid():
        form.save()
        return redirect("role_list")
    return render(request, "projects/role_form.html", {"form": form, "form_title": f"Edit Role: {role.name}"})


@login_required
def role_delete(request, pk):
    if not is_admin_role(request.user):
        return HttpResponseForbidden("Only admins can manage roles.")
    role = get_object_or_404(Role, pk=pk)
    if request.method == "POST":
        role.delete()
        return redirect("role_list")
    return render(request, "projects/role_confirm_delete.html", {"role": role})


@login_required
def task_list(request):
    tasks = Task.objects.select_related("project", "executor").prefetch_related("co_executors")
    return render(request, "projects/task_list.html", {"tasks": tasks})


@login_required
def task_create(request):
    if is_executor_role(request.user) and not can_manage_projects(request.user):
        return HttpResponseForbidden("Executors cannot create tasks.")
    form = TaskForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("task_list")
    return render(request, "projects/task_form.html", {"form": form, "form_title": "Create Task"})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not (is_admin(request.user) or task.can_update_status(request.user)):
        return HttpResponseForbidden("Only task participants can edit this task.")
    form = TaskForm(request.POST or None, instance=task)
    if form.is_valid():
        form.save()
        return redirect("task_list")
    return render(request, "projects/task_form.html", {"form": form, "form_title": f"Edit Task: {task.title}"})


@login_required
def task_delete(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only admins can delete tasks.")
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        task.delete()
        return redirect("task_list")
    return render(request, "projects/task_confirm_delete.html", {"task": task})


@login_required
def calendar_view(request):
    tasks = Task.objects.select_related("project", "executor").prefetch_related("co_executors").order_by("deadline")
    calendar = OrderedDict()
    no_deadline = []
    for task in tasks:
        if task.deadline:
            calendar.setdefault(task.deadline, []).append(task)
        else:
            no_deadline.append(task)
    return render(request, "projects/calendar.html", {"calendar": calendar, "no_deadline": no_deadline})


@require_POST
@login_required
def update_task_status(request):
    task_id = request.POST.get("task_id")
    status = request.POST.get("status")
    task = get_object_or_404(Task, pk=task_id)
    valid_statuses = [choice.value for choice in TaskStatus]
    if status not in valid_statuses:
        return JsonResponse({"ok": False, "error": "Invalid status"}, status=400)
    if not task.can_update_status(request.user):
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    task.status = status
    task.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": task.status, "overdue": task.is_overdue})
