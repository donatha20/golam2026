"""
Savings app configuration.
"""
from django.apps import AppConfig


class SavingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.savings'
    verbose_name = 'Savings Management'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.savings.signals
            print("✅ Savings signals imported successfully")
        except ImportError as e:
            print(f"❌ Error importing savings signals: {e}")
