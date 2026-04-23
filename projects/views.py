import calendar as cal_module
from collections import OrderedDict
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import GroupForm, ProjectForm, RoleForm, TaskForm, UserCreateForm, UserUpdateForm
from .html_sanitizer import sanitize_rich_text
from .models import Comment, Project, Role, Task, TaskActivity, TaskStatus

User = get_user_model()


def forbidden_response(request, message):
    return render(
        request,
        "projects/403.html",
        {"message": message},
        status=403,
    )


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
    return is_admin_role(user) or is_moderator_role(user) or has_role(user, "content") or has_role(user, "pm")


def can_manage_users(user):
    return is_admin_role(user)


def can_edit_project(user, project):
    if not user.is_authenticated:
        return False
    if project.owner_id == user.id:
        return True
    if is_admin_role(user):
        return True
    return has_role(user, "content") or has_role(user, "pm")


def can_delete_project(user, project):
    if not user.is_authenticated:
        return False
    if project.owner_id == user.id:
        return True
    return is_admin_role(user)


def get_user_projects(user):
    if is_admin_role(user) or has_role(user, "content"):
        return Project.objects.select_related("owner").prefetch_related("members")
    return (
        Project.objects.filter(
            models.Q(owner=user)
            | models.Q(members=user)
            | models.Q(tasks__executor=user)
            | models.Q(tasks__co_executors=user),
            hidden=False,
        )
        .distinct()
        .select_related("owner")
        .prefetch_related("members")
    )


def get_user_tasks(user):
    if is_admin_role(user) or has_role(user, "content"):
        return Task.objects.select_related("project", "executor").prefetch_related("co_executors")
    return (
        Task.objects.filter(
            models.Q(project__owner=user)
            | models.Q(executor=user),
            hidden=False,
            project__hidden=False,
        )
        .distinct()
        .select_related("project", "executor")
        .prefetch_related("co_executors")
    )


def can_view_project(user, project):
    if not user.is_authenticated:
        return False
    if is_admin_role(user) or has_role(user, "content"):
        return True
    if project.hidden:
        return False
    if project.owner_id == user.id:
        return True
    if project.members.filter(pk=user.pk).exists():
        return True
    return project.tasks.filter(models.Q(executor=user) | models.Q(co_executors=user)).exists()


def can_view_task(user, task):
    if not user.is_authenticated:
        return False
    if is_admin_role(user) or has_role(user, "content"):
        return True
    if task.hidden or task.project.hidden:
        return False
    if task.project.owner_id == user.id:
        return True
    if task.executor_id == user.id:
        return True
    return False


def can_edit_task(user, task):
    if not user.is_authenticated:
        return False
    if is_admin_role(user):
        return True
    if task.owner_id == user.id:
        return True
    return task.can_update_status(user)


def can_edit_task_progress(user, task):
    if not user.is_authenticated:
        return False
    if is_admin_role(user):
        return True
    if task.owner_id == user.id:
        return True
    if is_executor_role(user):
        return True
    return task.can_update_status(user)


def can_delete_task(user, task):
    if not user.is_authenticated:
        return False
    if is_admin_role(user):
        return True
    return task.owner_id == user.id


def can_view_all_activity_feed(user):
    return is_admin_role(user) or has_role(user, "content") or has_role(user, "pm")


def build_dashboard_activity_feed(user, offset=0, limit=20):
    if can_view_all_activity_feed(user):
        task_ids = list(Task.objects.values_list("pk", flat=True))
    else:
        task_ids = list(get_user_tasks(user).values_list("pk", flat=True))
    if not task_ids:
        return [], False, 0

    activities = list(
        TaskActivity.objects.filter(task_id__in=task_ids)
        .select_related("task", "task__project", "user")
        .order_by("-timestamp")[:limit]
    )
    comments = list(
        Comment.objects.filter(task_id__in=task_ids)
        .select_related("task", "task__project", "user")
        .order_by("-timestamp")[:limit]
    )

    feed_items = []
    for activity in activities:
        feed_items.append(
            {
                "kind": "activity",
                "kind_label": "Activity",
                "timestamp": activity.timestamp,
                "user": activity.user,
                "task": activity.task,
                "project": activity.task.project,
                "message": activity.message,
                "url": reverse("task_detail", args=[activity.task.pk]),
            }
        )
    for comment in comments:
        feed_items.append(
            {
                "kind": "comment",
                "kind_label": "Comment",
                "timestamp": comment.timestamp,
                "user": comment.user,
                "task": comment.task,
                "project": comment.task.project,
                "message": comment.text,
                "url": reverse("task_detail", args=[comment.task.pk]),
            }
        )

    feed_items.sort(key=lambda item: item["timestamp"], reverse=True)
    paged_items = feed_items[offset : offset + limit]
    next_offset = offset + len(paged_items)
    has_more = next_offset < len(feed_items)
    return paged_items, has_more, next_offset


@login_required
def dashboard(request):
    tasks = list(get_user_tasks(request.user))
    today = timezone.now().date()
    status_map = {status.value: status.label for status in TaskStatus}
    for task in tasks:
        if task.deadline is None:
            task.dashboard_deadline_class = ""
            task.dashboard_deadline_style = ""
        elif task.is_overdue:
            task.dashboard_deadline_class = "deadline--overdue"
            task.dashboard_deadline_style = "color: var(--md-error); font-weight: 600;"
        else:
            days_left = (task.deadline - today).days
            if days_left <= 3:
                task.dashboard_deadline_class = "deadline--soon"
                task.dashboard_deadline_style = "color: #f9a825; font-weight: 600;"
            else:
                task.dashboard_deadline_class = "deadline--future"
                task.dashboard_deadline_style = "color: #2e7d32; font-weight: 600;"
        task.dashboard_progress_width = max(0, min(100, task.progress or 0))
        task.dashboard_progress_label = f"{task.dashboard_progress_width}%"
    columns = [
        {
            "key": value,
            "label": label,
            "tasks": [task for task in tasks if task.status == value],
        }
        for value, label in status_map.items()
    ]

    visible_projects = get_user_projects(request.user)
    projects_count = visible_projects.count()
    groups_count = request.user.groups.count()
    task_pks = [task.pk for task in tasks]
    users_count = User.objects.filter(
        models.Q(projects__in=visible_projects)
        | models.Q(assigned_tasks__in=task_pks)
        | models.Q(supporting_tasks__in=task_pks)
    ).distinct().count()
    tasks_count = len(tasks)
    overdue_count = sum(1 for task in tasks if task.deadline and task.status != TaskStatus.DONE and task.deadline < today)

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
            "show_visibility_status": is_admin_role(request.user),
        },
    )


@login_required
def home(request):
    activity_feed, has_more, next_offset = build_dashboard_activity_feed(request.user, offset=0, limit=20)
    return render(
        request,
        "projects/home.html",
        {
            "activity_feed": activity_feed,
            "activity_feed_has_more": has_more,
            "activity_feed_next_offset": next_offset,
            "activity_feed_global": can_view_all_activity_feed(request.user),
        },
    )


@login_required
def dashboard_activity_feed(request):
    mode = request.GET.get("mode", "replace")
    try:
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        offset = 0
    try:
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        limit = 20
    offset = max(0, offset)
    limit = max(1, min(limit, 50))

    activity_feed, has_more, next_offset = build_dashboard_activity_feed(request.user, offset=offset, limit=limit)
    template_name = "projects/_dashboard_activity_feed_items.html" if mode == "append" else "projects/_dashboard_activity_feed_body.html"
    context = {
        "activity_feed": activity_feed,
        "activity_feed_has_more": has_more,
        "activity_feed_next_offset": next_offset,
    }
    feed_html = render_to_string(template_name, context, request=request)
    empty_html = ""
    if mode != "append" and not activity_feed:
        empty_html = render_to_string("projects/_dashboard_activity_feed_empty.html", request=request)
    return JsonResponse({
        "ok": True,
        "feed_html": feed_html,
        "empty_html": empty_html,
        "has_more": has_more,
        "next_offset": next_offset,
        "updated_at": timezone.now().isoformat(),
    })


@login_required
def project_list(request):
    projects = list(get_user_projects(request.user))
    for project in projects:
        project.can_edit = can_edit_project(request.user, project)
        project.can_delete = can_delete_project(request.user, project)
    return render(
        request,
        "projects/project_list.html",
        {
            "projects": projects,
            "can_manage_projects": can_manage_projects(request.user),
            "show_visibility_status": is_admin_role(request.user),
        },
    )


@login_required
def project_create(request):
    if not can_manage_projects(request.user):
        return forbidden_response(request, "Only admins, moderators, content, or pm can create projects.")
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        form.save_m2m()
        return redirect("project_list")
    return render(request, "projects/project_form.html", {"form": form, "form_title": "Create Project"})


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        return forbidden_response(request, "Only admin, content, pm, or owner can edit this project.")
    form = ProjectForm(request.POST or None, instance=project)
    if form.is_valid():
        form.save()
        return redirect("project_list")
    return render(request, "projects/project_form.html", {"form": form, "form_title": f"Edit Project: {project.title}"})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_delete_project(request.user, project):
        return forbidden_response(request, "Only admin or owner can delete this project.")

    delete_blocked = False
    if request.method == "POST":
        if project.tasks.exists():
            delete_blocked = True
        else:
            project.delete()
            return redirect("project_list")

    return render(
        request,
        "projects/project_confirm_delete.html",
        {"project": project, "delete_blocked": delete_blocked},
    )


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("owner").prefetch_related("members", "tasks__executor", "tasks__co_executors"),
        pk=pk,
    )
    if not can_view_project(request.user, project):
        return forbidden_response(request, "You do not have access to view this project.")
    tasks = project.tasks.select_related("executor").prefetch_related("co_executors")
    if not (is_admin_role(request.user) or has_role(request.user, "content")):
        tasks = tasks.filter(hidden=False)
    for task in tasks:
        task.progress_width = max(0, min(100, task.progress or 0))
    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "tasks": tasks,
            "can_edit_project": can_edit_project(request.user, project),
            "can_delete_project": can_delete_project(request.user, project),
            "show_visibility_status": is_admin_role(request.user),
        },
    )


@login_required
def user_list(request):
    if not can_manage_users(request.user):
        return forbidden_response(request, "Only admins can manage users.")
    users = User.objects.order_by("username").prefetch_related(
        "groups", "projects", "assigned_tasks", "supporting_tasks", "roles"
    )
    return render(request, "projects/user_list.html", {"users": users})


@login_required
def user_create(request):
    if not can_manage_users(request.user):
        return forbidden_response(request, "Only admins can manage users.")
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "projects/user_form.html", {"form": form, "form_title": "Create User"})


@login_required
def user_update(request, pk):
    if not can_manage_users(request.user):
        return forbidden_response(request, "Only admins can manage users.")
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "projects/user_form.html", {"form": form, "form_title": f"Edit User: {user.username}"})


@login_required
def user_delete(request, pk):
    if not can_manage_users(request.user):
        return forbidden_response(request, "Only admins can manage users.")
    user = get_object_or_404(User, pk=pk)
    admin_user_blocked = user.username.lower() == "admin"
    delete_blocked = (
        admin_user_blocked,
        user.owned_projects.exists()
        or user.projects.exists()
        or user.assigned_tasks.exists()
        or user.supporting_tasks.exists()
    )
    deletion_reason = (
        "The admin user cannot be deleted."
        if admin_user_blocked
        else "This user is linked to projects or tasks and cannot be deleted until those links are removed."
    )
    if request.method == "POST":
        if delete_blocked:
            return render(
                request,
                "projects/user_confirm_delete.html",
                {"user": user, "delete_blocked": True, "deletion_reason": deletion_reason},
            )
        user.delete()
        return redirect("user_list")
    return render(
        request,
        "projects/user_confirm_delete.html",
        {"user": user, "delete_blocked": delete_blocked, "deletion_reason": deletion_reason},
    )


@login_required
def group_list(request):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage groups.")
    groups = Group.objects.order_by("name")
    return render(request, "projects/group_list.html", {"groups": groups})


@login_required
def group_create(request):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage groups.")
    form = GroupForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("group_list")
    return render(request, "projects/group_form.html", {"form": form, "form_title": "Create Group"})


@login_required
def group_update(request, pk):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage groups.")
    group = get_object_or_404(Group, pk=pk)
    form = GroupForm(request.POST or None, instance=group)
    if form.is_valid():
        form.save()
        return redirect("group_list")
    return render(request, "projects/group_form.html", {"form": form, "form_title": f"Edit Group: {group.name}"})


@login_required
def group_delete(request, pk):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage groups.")
    group = get_object_or_404(Group, pk=pk)
    if request.method == "POST":
        group.delete()
        return redirect("group_list")
    return render(request, "projects/group_confirm_delete.html", {"group": group})


@login_required
def role_list(request):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage roles.")
    roles = Role.objects.prefetch_related("users").order_by("name")
    return render(request, "projects/role_list.html", {"roles": roles})


@login_required
def role_create(request):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage roles.")
    form = RoleForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("role_list")
    return render(request, "projects/role_form.html", {"form": form, "form_title": "Create Role"})


@login_required
def role_update(request, pk):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage roles.")
    role = get_object_or_404(Role, pk=pk)
    if role.is_protected:
        return render(request, "projects/role_protected.html", {"role": role})
    form = RoleForm(request.POST or None, instance=role)
    if form.is_valid():
        form.save()
        return redirect("role_list")
    return render(request, "projects/role_form.html", {"form": form, "form_title": f"Edit Role: {role.name}"})


@login_required
def role_delete(request, pk):
    if not is_admin_role(request.user):
        return forbidden_response(request, "Only admins can manage roles.")
    role = get_object_or_404(Role, pk=pk)
    if role.is_protected:
        return forbidden_response(request, "This role is protected and cannot be deleted.")
    if request.method == "POST":
        role.delete()
        return redirect("role_list")
    return render(request, "projects/role_confirm_delete.html", {"role": role})


@login_required
def task_list(request):
    tasks = get_user_tasks(request.user).select_related("project", "executor").prefetch_related("co_executors")
    projects = get_user_projects(request.user)

    project_id = request.GET.get("project", "").strip()
    status = request.GET.get("status", "").strip()
    executor_id = request.GET.get("executor", "").strip()
    deadline_from_raw = request.GET.get("deadline_from", "").strip()
    deadline_to_raw = request.GET.get("deadline_to", "").strip()
    deadline_from = parse_date(deadline_from_raw)
    deadline_to = parse_date(deadline_to_raw)

    if project_id and project_id.isdigit():
        tasks = tasks.filter(project_id=int(project_id))
    if status and status in TaskStatus.values:
        tasks = tasks.filter(status=status)
    if executor_id and executor_id.isdigit():
        tasks = tasks.filter(executor_id=int(executor_id))
    if deadline_from:
        tasks = tasks.filter(deadline__gte=deadline_from)
    if deadline_to:
        tasks = tasks.filter(deadline__lte=deadline_to)

    tasks = list(tasks)
    for task in tasks:
        task.can_edit = can_edit_task(request.user, task)
        task.can_delete = can_delete_task(request.user, task)

    executors = User.objects.filter(
        assigned_tasks__isnull=False
    ).distinct().order_by("username")

    return render(
        request,
        "projects/task_list.html",
        {
            "tasks": tasks,
            "projects": projects,
            "task_status_choices": TaskStatus.choices,
            "executors": executors,
            "show_visibility_status": is_admin_role(request.user),
            "filters": {
                "project": project_id,
                "status": status,
                "executor": executor_id,
                "deadline_from": deadline_from_raw,
                "deadline_to": deadline_to_raw,
            },
        },
    )


@login_required
def task_detail(request, pk):
    task = get_object_or_404(
        Task.objects.select_related("project", "executor").prefetch_related("co_executors", "activities__user", "comments__user"),
        pk=pk,
    )
    if not can_view_task(request.user, task):
        return forbidden_response(request, "You do not have access to view this task.")
    activities = task.activities.select_related("user")
    comments = task.comments.select_related("user")
    return render(
        request,
        "projects/task_detail.html",
        {
            "task": task,
            "can_edit_task": can_edit_task(request.user, task),
            "can_edit_task_progress": can_edit_task_progress(request.user, task),
            "can_delete_task": can_delete_task(request.user, task),
            "show_visibility_status": is_admin_role(request.user),
            "activities": activities,
            "comments": comments,
        },
    )


@require_POST
@login_required
def add_task_comment(request, pk):
    task = get_object_or_404(
        Task.objects.select_related("project", "executor").prefetch_related("co_executors", "comments__user"),
        pk=pk,
    )
    if not can_view_task(request.user, task):
        return JsonResponse({"ok": False, "error": "You do not have access to comment on this task."}, status=403)

    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Comment text cannot be empty."}, status=400)

    Comment.objects.create(task=task, user=request.user, text=sanitize_rich_text(text))
    comments = task.comments.select_related("user")
    comments_html = render_to_string(
        "projects/_task_comments.html",
        {"task": task, "comments": comments},
        request=request,
    )
    return JsonResponse({"ok": True, "comments_html": comments_html})


@require_POST
@login_required
def update_task_progress(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_edit_task_progress(request.user, task):
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)

    progress_raw = request.POST.get("progress", "").strip()
    try:
        progress = int(progress_raw)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid progress value"}, status=400)

    if progress < 0 or progress > 100:
        return JsonResponse({"ok": False, "error": "Progress must be between 0 and 100"}, status=400)

    task.progress = progress
    task.save(update_fields=["progress"])
    return JsonResponse({"ok": True, "progress": task.progress})


@login_required
def task_create(request):
    form = TaskForm(request.POST or None, user=request.user)
    if form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        if is_executor_role(request.user) and not request.user.is_superuser:
            task.executor = request.user
        task.save()
        form.save_m2m()
        if is_executor_role(request.user) and not request.user.is_superuser:
            task.co_executors.clear()
        return redirect("task_list")
    return render(request, "projects/task_form.html", {"form": form, "form_title": "Create Task"})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not (is_admin_role(request.user) or task.can_update_status(request.user)):
        if task.owner_id != request.user.id:
            return forbidden_response(request, "Only task participants or the task owner can edit this task.")
    form = TaskForm(request.POST or None, instance=task, user=request.user)
    if form.is_valid():
        form.save()
        return redirect("task_list")
    return render(request, "projects/task_form.html", {"form": form, "form_title": f"Edit Task: {task.title}"})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_delete_task(request.user, task):
        return forbidden_response(request, "Only admins or the task owner can delete this task.")
    if request.method == "POST":
        task.delete()
        return redirect("task_list")
    return render(request, "projects/task_confirm_delete.html", {"task": task})


@login_required
def calendar_view(request):
    today = date.today()

    # allow ?month=YYYY-MM to navigate
    month_str = request.GET.get("month", "")
    try:
        year, month = int(month_str.split("-")[0]), int(month_str.split("-")[1])
    except Exception:
        year, month = today.year, today.month

    # clamp to valid range
    if not (1 <= month <= 12):
        year, month = today.year, today.month

    prev_month = month - 1 or 12
    prev_year  = year if month > 1 else year - 1
    next_month = month % 12 + 1
    next_year  = year if month < 12 else year + 1

    tasks = get_user_tasks(request.user).order_by("deadline")

    tasks_by_date = {}
    no_deadline = []
    for task in tasks:
        if task.deadline:
            tasks_by_date.setdefault(task.deadline, []).append(task)
        else:
            no_deadline.append(task)

    # build weeks grid: list of weeks, each week = list of date|None (padding with None)
    cal = cal_module.Calendar(firstweekday=0)  # Monday first
    month_days = cal.monthdatescalendar(year, month)  # list of 7-day weeks

    weeks = []
    for week in month_days:
        week_cells = []
        for d in week:
            week_cells.append({
                "date": d,
                "in_month": d.month == month,
                "is_today": d == today,
                "tasks": tasks_by_date.get(d, []),
            })
        weeks.append(week_cells)

    return render(request, "projects/calendar.html", {
        "weeks": weeks,
        "year": year,
        "month": month,
        "month_name": cal_module.month_name[month],
        "today": today,
        "no_deadline": no_deadline,
        "prev": f"{prev_year}-{prev_month:02d}",
        "next": f"{next_year}-{next_month:02d}",
        "weekday_names": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    })


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
