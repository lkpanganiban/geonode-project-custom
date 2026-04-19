from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TaskTriggerHistory(models.Model):
    """Store history of manually triggered tasks"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILURE', 'Failure'),
        ('RETRY', 'Retry'),
        ('REVOKED', 'Revoked'),
    ]
    
    task_id = models.CharField(max_length=255, unique=True, help_text="Celery task ID")
    task_name = models.CharField(max_length=255, help_text="Task name/path")
    args = models.JSONField(default=list, blank=True, help_text="Task arguments")
    kwargs = models.JSONField(default=dict, blank=True, help_text="Task keyword arguments")
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='triggered_tasks')
    triggered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    result = models.TextField(blank=True, null=True, help_text="Task result or error message")
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
        verbose_name = 'Task Trigger History'
        verbose_name_plural = 'Task Trigger Histories'
    
    def __str__(self):
        return f"{self.task_name} ({self.task_id[:8]}) - {self.status}"
