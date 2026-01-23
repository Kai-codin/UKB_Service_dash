from django.db import models
from django.contrib.auth import get_user_model


class Site(models.Model):
    name = models.CharField(max_length=200)
    base_dir = models.CharField(max_length=1024, help_text='Base directory for site')
    base_command = models.CharField(max_length=1024, default='sudo docker compose exec web python manage.py')

    def __str__(self):
        return self.name


class Command(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='commands')
    name = models.CharField(max_length=200)
    command_string = models.CharField(max_length=1024)
    active = models.BooleanField(default=True)

    class Meta:
        # Django automatically creates add/change/delete permissions for models.
        # Only add custom permissions that don't clash with built-ins.
        permissions = [
            ('view_logs', 'Can view logs'),
        ]

    def __str__(self):
        return f"{self.site.name} - {self.name}"


class Log(models.Model):
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True)
    command = models.ForeignKey(Command, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, default='INFO')
    message = models.TextField()

    def __str__(self):
        return f"[{self.created_at}] {self.level} - {self.message[:80]}"


class CommandRun(models.Model):
    command = models.ForeignKey(Command, on_delete=models.CASCADE, related_name='runs')
    pid = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    manually_stopped = models.BooleanField(default=False)
    restart_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        status = 'stopped' if self.stopped_at else 'running'
        return f"{self.command} ({status}) pid={self.pid}"
