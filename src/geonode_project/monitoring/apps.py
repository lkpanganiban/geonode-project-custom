from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'geonode_project.monitoring'
    verbose_name = _('Celery Monitoring')
    
    def ready(self):
        # Import tasks to ensure they're registered with Celery
        import geonode_project.monitoring.tasks  # noqa
