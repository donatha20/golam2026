"""
URL configuration for financial statements app.
"""
from django.urls import path
from . import views

app_name = 'financial_statements'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('api/financial-summary/', views.financial_summary_api, name='financial_summary_api'),
    
    # Statement Generation
    path('generate/', views.generate_statement, name='generate_statement'),
    path('view/<int:run_id>/', views.view_statement, name='view_statement'),
    path('runs/', views.statement_runs, name='statement_runs'),
    
    # Export Functions
    path('export/pdf/<int:run_id>/', views.export_pdf, name='export_pdf'),
    path('export/excel/<int:run_id>/', views.export_excel, name='export_excel'),
    
    # Period Management
    path('periods/', views.manage_periods, name='manage_periods'),
    path('periods/add/', views.add_period, name='add_period'),
    path('periods/<int:period_id>/close/', views.close_period, name='close_period'),
    
    # Account Classifications
    path('classifications/', views.manage_classifications, name='manage_classifications'),
    path('classifications/add/', views.add_classification, name='add_classification'),

    # Specific Financial Reports
    path('reports/trial-balance/', views.trial_balance_report, name='trial_balance_report'),
    path('reports/balance-sheet/', views.balance_sheet_report, name='balance_sheet_report'),
    path('reports/income-statement/', views.income_statement_report, name='income_statement_report'),
    path('reports/cash-flow/', views.cash_flow_report, name='cash_flow_report'),
    path('reports/portfolio-analysis/', views.portfolio_analysis_report, name='portfolio_analysis_report'),
    path('reports/loan-aging/', views.loan_aging_report, name='loan_aging_report'),
    path('reports/collection-summary/', views.collection_summary_report, name='collection_summary_report'),
]
