from django.contrib import admin

from .models import Project, Role, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")
    search_fields = ("title", "description", "owner__username")
    filter_horizontal = ("members",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    filter_horizontal = ("users",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "executor", "deadline")
    list_filter = ("status", "project")
    search_fields = ("title", "description", "executor__username")
    filter_horizontal = ("co_executors",)
