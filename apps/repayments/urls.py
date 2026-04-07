"""
URL patterns for repayment management.
"""
from django.urls import path
from . import views

app_name = 'repayments'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Main Repayment Functions
    path('record/', views.record_payment, name='record_repayment'),
    path('list/', views.payment_list, name='payment_list'),
    path('overdue/', views.overdue_payments, name='overdue_payments'),
    path('bulk/', views.bulk_payments, name='bulk_payments'),
    path('bulk/download-template/', views.download_bulk_template, name='download_template'),
    path('reports/', views.payment_reports, name='payment_reports'),
    path('collection-report/', views.collection_report, name='collection_report'),
    
    # Payment Details and Processing
    path('payment/<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('process/', views.process_payment, name='process_payment'),
    path('reverse/<int:payment_id>/', views.reverse_payment, name='reverse_payment'),
    
    # Repayment Schedules
    path('schedule/<int:loan_id>/', views.repayment_schedule, name='repayment_schedule'),
    path('loan-repayments/<int:loan_id>/', views.loan_repayments, name='loan_repayments'),
    
    # Outstanding Balances
    path('outstanding/', views.outstanding_balances, name='outstanding_balances'),
    
    # Collection Management
    path('collections/', views.daily_collections_dashboard, name='daily_collections_dashboard'),
    path('collections/collector/<int:collector_id>/', views.collector_collections, name='collector_collections'),
    path('collections/validation/', views.collection_validation, name='collection_validation'),
    path('collections/validate/<int:collection_id>/', views.validate_collection, name='validate_collection'),
    path('collections/summary/', views.collection_summary, name='collection_summary'),

    # API endpoints for AJAX calls
    path('api/loan-info/<int:loan_id>/', views.loan_info_api, name='loan_info_api'),
    path('api/calculate-allocation/<int:loan_id>/<str:amount>/', views.calculate_allocation_api, name='calculate_allocation_api'),
    path('api/quick-amount/<int:loan_id>/<str:amount_type>/', views.quick_amount_api, name='quick_amount_api'),
    path('api/loan-balance/<int:loan_id>/', views.get_loan_balance, name='get_loan_balance'),
    path('api/payment-allocation/', views.calculate_payment_allocation, name='calculate_payment_allocation'),
    path('api/collection-data/<int:collection_id>/', views.get_collection_data, name='get_collection_data'),
    path('api/recalculate-collection/<int:collection_id>/', views.recalculate_collection, name='recalculate_collection'),
    path('api/generate-summary/', views.generate_daily_summary, name='generate_daily_summary'),
]


