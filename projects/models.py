from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_projects")
    members = models.ManyToManyField(User, blank=True, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def can_manage(self, user):
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        if self.owner_id == user.id:
            return True
        return user.groups.filter(name="Admins").exists()


class TaskStatus(models.TextChoices):
    TODO = "ToDo", "To Do"
    IN_PROGRESS = "InProgress", "In Progress"
    REVIEW = "Review", "Review"
    DONE = "Done", "Done"


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
    )
    deadline = models.DateField(null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    executor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    co_executors = models.ManyToManyField(User, blank=True, related_name="supporting_tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["deadline", "title"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if not self.deadline:
            return False
        return self.status != TaskStatus.DONE and timezone.now().date() > self.deadline

    def can_update_status(self, user):
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        if self.executor_id == user.id:
            return True
        return self.co_executors.filter(pk=user.id).exists()
