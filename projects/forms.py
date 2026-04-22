from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import Project, Task, TaskStatus

User = get_user_model()


class UserCreateForm(UserCreationForm):
    projects = forms.ModelMultipleChoiceField(
        label="Member of projects",
        queryset=Project.objects.all(),
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
        ]
        widgets = {
            "groups": forms.SelectMultiple(attrs={"size": 6}),
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.projects.set(self.cleaned_data["projects"])
        return user


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]
        labels = {"name": "Group Name"}


class UserUpdateForm(forms.ModelForm):
    projects = forms.ModelMultipleChoiceField(
        label="Member of projects",
        queryset=Project.objects.all(),
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
        ]
        widgets = {
            "groups": forms.SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["projects"].initial = self.instance.projects.all()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.projects.set(self.cleaned_data["projects"])
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
