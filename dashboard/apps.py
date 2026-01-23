from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        # start the supervisor thread when the app is ready
        try:
            from . import supervisor
            supervisor.supervisor.start()
        except Exception:
            pass
