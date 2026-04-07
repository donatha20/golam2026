from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        # Register auth signal handlers (login/logout session audit tracking).
        from . import signals  # noqa: F401
