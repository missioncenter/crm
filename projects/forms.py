from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import Project, Role, Task, TaskStatus

User = get_user_model()


class UserCreateForm(UserCreationForm):
    projects = forms.ModelMultipleChoiceField(
        label="Member of projects",
        queryset=Project.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )
    roles = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Role.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
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
            "groups": forms.SelectMultiple(attrs={"size": 6}),
            "roles": forms.SelectMultiple(attrs={"size": 6}),
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
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )

    class Meta:
        model = Role
        fields = ["name", "description", "users"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "users": forms.SelectMultiple(attrs={"size": 6}),
        }


class UserUpdateForm(forms.ModelForm):
    projects = forms.ModelMultipleChoiceField(
        label="Member of projects",
        queryset=Project.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )
    roles = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Role.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
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
            "groups": forms.SelectMultiple(attrs={"size": 6}),
            "roles": forms.SelectMultiple(attrs={"size": 6}),
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
        fields = ["title", "description", "owner", "members"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "members": forms.SelectMultiple(attrs={"size": 6}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "deadline",
            "project",
            "executor",
            "co_executors",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "co_executors": forms.SelectMultiple(attrs={"size": 6}),
        }
        labels = {
            "co_executors": "Co-executors",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        executor_queryset = User.objects.filter(roles__name__iexact="executor").distinct().order_by("username")
        if self.instance and self.instance.pk and self.instance.executor:
            executor_queryset = executor_queryset | User.objects.filter(pk=self.instance.executor.pk)
        self.fields["executor"].queryset = executor_queryset

        co_executor_queryset = User.objects.filter(roles__name__iexact="executor").distinct().order_by("username")
        if self.instance and self.instance.pk:
            co_executor_queryset = co_executor_queryset | self.instance.co_executors.all()
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
