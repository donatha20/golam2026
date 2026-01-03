"""
URL patterns for savings management.
"""
from django.urls import path
from . import views

app_name = 'savings'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # View Categories Section
    path('categories/', views.view_categories, name='view_categories'),
    path('categories/create/', views.create_categories, name='create_categories'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    
    # Charges Management
    path('charges/set/', views.set_charges, name='set_charges'),
    path('charges/withdraw/set/', views.set_withdraw_charges, name='set_withdraw_charges'),
    path('charges/service/set/', views.set_service_charges, name='set_service_charges'),
    path('charges/withdraw/view/', views.view_withdraw_charges, name='view_withdraw_charges'),
    path('charges/service/view/', views.view_service_charges, name='view_service_charges'),
    path('charges/', views.view_charges, name='view_charges'),
    path('charges/<int:charge_id>/edit/', views.edit_charge, name='edit_charge'),
    path('charges/<int:charge_id>/delete/', views.delete_charge, name='delete_charge'),
    
    # Account Management
    path('accounts/', views.view_accounts, name='view_accounts'),
    path('accounts/list/', views.account_list, name='account_list'),
    path('accounts/open/', views.open_account, name='open_account'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('transactions/record/<str:transaction_type>/', views.record_transaction, name='record_transaction'),
    path('transactions/deposit/', views.record_deposited, name='record_deposited'),
    path('transactions/withdraw/', views.record_withdrawn, name='record_withdrawn'),
    path('transactions/charges/', views.record_charges, name='record_charges'),
    path('transactions/interest/', views.record_earned_interest, name='record_earned_interest'),
    
    # Transaction Views
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/deposited/', views.view_deposited, name='view_deposited'),
    path('transactions/withdrawn/', views.view_withdrawn, name='view_withdrawn'),
    path('transactions/charges/view/', views.view_charges, name='view_charges'),
    path('transactions/interests/', views.view_interests, name='view_interests'),
    path('transactions/process/', views.process_transaction, name='process_transaction'),
    path('transactions/<int:transaction_id>/detail/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:transaction_id>/reverse/', views.reverse_transaction, name='reverse_transaction'),
    path('accounts/balance/', views.view_balance, name='view_balance'),
    
    # Interest and Reports
    path('interest/', views.interest_calculation, name='interest_calculation'),
    path('reports/', views.reports, name='reports'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # API endpoints
    path('api/check-eligibility/', views.check_loan_eligibility_api, name='check_loan_eligibility_api'),
    path('api/balance/<str:account_number>/', views.account_balance_api, name='account_balance_api'),
]
