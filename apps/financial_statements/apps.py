from django.apps import AppConfig


class FinancialStatementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.financial_statements'
    verbose_name = 'Financial Statements'
    
    def ready(self):
        import apps.financial_statements.signals


