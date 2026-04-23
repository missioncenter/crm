from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.db import models

from .html_sanitizer import sanitize_rich_text
from .models import Project, Role, Task, TaskStatus

User = get_user_model()


class UserCreateForm(UserCreationForm):
    projects = forms.ModelMultipleChoiceField(
        label="Member of projects",
        queryset=Project.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )
    roles = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Role.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "groups",
            "projects",
            "roles",
        ]
        widgets = {
            "groups": forms.SelectMultiple(attrs={"size": 10}),
            "roles": forms.SelectMultiple(attrs={"size": 10}),
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.projects.set(self.cleaned_data["projects"])
            user.roles.set(self.cleaned_data["roles"])
        return user


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]
        labels = {"name": "Group Name"}


class RoleForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )

    class Meta:
        model = Role
        fields = ["name", "description", "users"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "data-wysiwyg-textarea": "true"}),
            "users": forms.SelectMultiple(attrs={"size": 10}),
        }

    def clean_description(self):
        return sanitize_rich_text(self.cleaned_data.get("description", ""))


class UserUpdateForm(forms.ModelForm):
    projects = forms.ModelMultipleChoiceField(
        label="Member of projects",
        queryset=Project.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )
    roles = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Role.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "groups",
            "projects",
            "roles",
        ]
        widgets = {
            "groups": forms.SelectMultiple(attrs={"size": 10}),
            "roles": forms.SelectMultiple(attrs={"size": 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["projects"].initial = self.instance.projects.all()
            self.fields["roles"].initial = self.instance.roles.all()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.projects.set(self.cleaned_data["projects"])
            user.roles.set(self.cleaned_data["roles"])
        return user


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "description", "members", "hidden"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "data-wysiwyg-textarea": "true"}),
            "members": forms.SelectMultiple(attrs={"size": 10}),
        }
        labels = {
            "hidden": "Hidden",
        }

    def clean_description(self):
        return sanitize_rich_text(self.cleaned_data.get("description", ""))


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "deadline",
            "progress",
            "project",
            "executor",
            "co_executors",
            "hidden",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "data-wysiwyg-textarea": "true"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "progress": forms.NumberInput(attrs={"min": 0, "max": 100, "step": 1}),
            "co_executors": forms.SelectMultiple(attrs={"size": 10}),
        }
        labels = {
            "co_executors": "Co-executors",
            "hidden": "Hidden",
            "progress": "Progress",
        }

    def clean_description(self):
        return sanitize_rich_text(self.cleaned_data.get("description", ""))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_executor = User.objects.filter(roles__name__iexact="executor")
        if self.instance and self.instance.pk and self.instance.executor:
            executor_queryset = User.objects.filter(
                models.Q(roles__name__iexact="executor") | models.Q(pk=self.instance.executor.pk)
            ).distinct().order_by("username")
        else:
            executor_queryset = base_executor.distinct().order_by("username")
        self.fields["executor"].queryset = executor_queryset

        base_co_executor = User.objects.filter(roles__name__iexact="executor")
        if self.instance and self.instance.pk:
            co_executor_queryset = User.objects.filter(
                models.Q(roles__name__iexact="executor") | models.Q(pk__in=self.instance.co_executors.values_list("pk", flat=True))
            ).distinct().order_by("username")
        else:
            co_executor_queryset = base_co_executor.distinct().order_by("username")
        self.fields["co_executors"].queryset = co_executor_queryset

    def clean_executor(self):
        executor = self.cleaned_data.get("executor")
        if executor is None:
            return executor
        if not executor.roles.filter(name__iexact="executor").exists():
            raise forms.ValidationError("Executor must have the executor role.")
        return executor

    def clean_co_executors(self):
        co_executors = self.cleaned_data.get("co_executors")
        invalid = [user.username for user in co_executors if not user.roles.filter(name__iexact="executor").exists()]
        if invalid:
            raise forms.ValidationError(
                "Co-executors must have the executor role: %(users)s",
                params={"users": ", ".join(invalid)},
            )
        return co_executors

    def clean_progress(self):
        progress = self.cleaned_data.get("progress")
        if progress is None:
            return 0
        if progress < 0 or progress > 100:
            raise forms.ValidationError("Progress must be between 0 and 100.")
        return progress
