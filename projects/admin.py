from django import forms
from django.contrib import admin

from .models import Comment, Project, Role, Task, TaskActivity


class TaskAdminForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = "__all__"

    def clean_progress(self):
        progress = self.cleaned_data.get("progress")
        if progress is None:
            return 0
        if progress < 0 or progress > 100:
            raise forms.ValidationError("Progress must be between 0 and 100.")
        return progress


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
    form = TaskAdminForm
    list_display = ("title", "project", "status", "progress", "executor", "deadline")
    list_filter = ("status", "project")
    search_fields = ("title", "description", "executor__username")
    filter_horizontal = ("co_executors",)


@admin.register(TaskActivity)
class TaskActivityAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("task__title", "message", "user__username")
    readonly_fields = ("task", "user", "message", "timestamp")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("task__title", "text", "user__username")
    readonly_fields = ("task", "user", "text", "timestamp")
