"""
App configuration for the payroll app.
"""
from django.apps import AppConfig


class PayrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payroll'
    verbose_name = 'Employee Payroll'
    
    def ready(self):
        import apps.payroll.signals
