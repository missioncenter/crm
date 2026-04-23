from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .current_user import get_current_user

User = get_user_model()


class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_projects")
    members = models.ManyToManyField(User, blank=True, related_name="projects")
    hidden = models.BooleanField(default=False)
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

    @property
    def deadline(self):
        latest_task = self.tasks.filter(deadline__isnull=False).order_by("-deadline").first()
        return latest_task.deadline if latest_task else None

    @property
    def deadline_tasks_count(self):
        return self.tasks.filter(deadline__isnull=False).count()

    @property
    def days_until_deadline(self):
        if self.deadline is None:
            return None
        return (self.deadline - timezone.now().date()).days

    @property
    def deadline_days_remaining(self):
        days = self.days_until_deadline
        return None if days is None else abs(days)

    @property
    def deadline_label(self):
        if self.deadline is None:
            return "No deadline"
        days = self.days_until_deadline
        if days < 0:
            return f"Overdue by {self.deadline_days_remaining} days"
        if days == 0:
            return "Due today"
        if days == 1:
            return "1 day left"
        return f"{days} days left"


class Role(models.Model):
    PROTECTED_NAMES = frozenset({"admin", "executor", "content", "guest", "auditor", "pm"})

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(User, blank=True, related_name="roles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_protected(self):
        return self.name.lower() in self.PROTECTED_NAMES

    @classmethod
    def is_protected_name(cls, name):
        return name and name.lower() in cls.PROTECTED_NAMES


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
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    executor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    co_executors = models.ManyToManyField(User, blank=True, related_name="supporting_tasks")
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["deadline", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.progress is None:
            return
        if self.progress < 0 or self.progress > 100:
            raise ValidationError({"progress": "Progress must be between 0 and 100."})

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        update_fields_set = set(update_fields) if update_fields is not None else None
        if update_fields is not None:
            kwargs["update_fields"] = update_fields_set
        tracked_fields = {"status", "executor"}
        old_task = None

        if self.pk and (update_fields_set is None or tracked_fields.intersection(update_fields_set)):
            old_task = Task.objects.select_related("executor").filter(pk=self.pk).first()

        super().save(*args, **kwargs)

        if not old_task:
            return

        changes = []
        if old_task.status != self.status:
            changes.append(f"Status changed from {TaskStatus(old_task.status).label} to {self.get_status_display()}")
        if old_task.executor_id != self.executor_id:
            old_executor = old_task.executor.username if old_task.executor else "Unassigned"
            new_executor = self.executor.username if self.executor else "Unassigned"
            changes.append(f"Executor changed from {old_executor} to {new_executor}")

        if not changes:
            return

        actor = get_current_user()
        TaskActivity.objects.create(
            task=self,
            user=actor if actor and actor.is_authenticated else None,
            message="; ".join(changes),
        )

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


class TaskActivity(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="task_activities")
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.task.title}: {self.message}"


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="task_comments")
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.title}"
