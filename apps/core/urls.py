"""
Core URL configuration for the microfinance system.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),

    # User Management URLs
    path('users/', views.user_list, name='user_list'),
    path('users/logs/', views.user_logs, name='user_logs'),
    path('users/add/', views.add_user, name='add_user'),

    # Settings URLs
    path('settings/', views.settings_dashboard, name='settings_dashboard'),
    path('settings/system/', views.system_settings, name='system_settings'),
    
    # Company Info URLs
    path('settings/company/', views.company_profile, name='company_profile'),
    path('settings/company/update/', views.update_company_info, name='update_company_info'),
    
    # Working Mode URLs
    path('settings/working-mode/', views.working_mode_settings, name='working_mode_settings'),
    path('settings/working-mode/view/', views.view_working_mode, name='view_working_mode'),
    path('settings/working-mode/add/', views.add_working_mode, name='add_working_mode'),
    path('settings/working-modes/', views.view_working_modes, name='view_working_modes'),
    path('settings/working-modes/<int:mode_id>/edit/', views.edit_working_mode, name='edit_working_mode'),
    path('settings/working-modes/<int:mode_id>/delete/', views.delete_working_mode, name='delete_working_mode'),
    
    # Public Holidays URLs
    path('settings/holidays/add/', views.add_holiday, name='add_holiday'),
    path('settings/holidays/', views.view_holidays, name='view_holidays'),
    path('settings/holidays/<int:holiday_id>/edit/', views.edit_holiday, name='edit_holiday'),
    path('settings/holidays/<int:holiday_id>/delete/', views.delete_holiday, name='delete_holiday'),
    
    # Branches URLs
    path('settings/branches/add/', views.add_branch, name='add_branch'),
    path('settings/branches/', views.view_branches, name='view_branches'),
    path('settings/branches/<int:branch_id>/edit/', views.edit_branch, name='edit_branch'),
    path('settings/branches/<int:branch_id>/delete/', views.delete_branch, name='delete_branch'),
    path('settings/branches/', views.branch_management, name='branch_management'),
    
    # Loan Categories URLs
    path('settings/loan-categories/add/', views.add_loan_category, name='add_loan_category'),
    path('settings/loan-categories/', views.view_loan_categories, name='view_loan_categories'),
    path('settings/loan-categories/<int:category_id>/edit/', views.edit_loan_category, name='edit_loan_category'),
    path('settings/loan-categories/<int:category_id>/delete/', views.delete_loan_category, name='delete_loan_category'),
    path('settings/loan-categories/', views.loan_categories, name='loan_categories'),
    
    # Loan Sectors URLs
    path('settings/loan-sectors/add/', views.add_loan_sector, name='add_loan_sector'),
    path('settings/loan-sectors/', views.view_loan_sectors, name='view_loan_sectors'),
    path('settings/loan-sectors/<int:sector_id>/edit/', views.edit_loan_sector, name='edit_loan_sector'),
    path('settings/loan-sectors/<int:sector_id>/delete/', views.delete_loan_sector, name='delete_loan_sector'),
    
    # Penalty Configurations URLs
    path('settings/penalties/add/', views.add_penalty_configuration, name='add_penalty_configuration'),
    path('settings/penalties/', views.view_penalty_configurations, name='view_penalty_configurations'),
    path('settings/penalties/<int:penalty_id>/edit/', views.edit_penalty_configuration, name='edit_penalty_configuration'),
    path('settings/penalties/<int:penalty_id>/delete/', views.delete_penalty_configuration, name='delete_penalty_configuration'),
    path('settings/penalties/', views.penalty_configurations, name='penalty_configurations'),
    
    # Penalty Settings URLs (alias for penalty configurations)
    path('settings/penalty-settings/add/', views.add_penalty_setting, name='add_penalty_setting'),
    path('settings/penalty-settings/', views.view_penalty_settings, name='view_penalty_settings'),
    path('settings/penalty-settings/<int:penalty_id>/edit/', views.edit_penalty_configuration, name='edit_penalty_setting'),
    path('settings/penalty-settings/<int:penalty_id>/delete/', views.delete_penalty_configuration, name='delete_penalty_setting'),
    
    # Income Sources URLs
    path('settings/income-sources/add/', views.add_income_source, name='add_income_source'),
    path('settings/income-sources/', views.view_income_sources, name='view_income_sources'),
    path('settings/income-sources/<int:source_id>/edit/', views.edit_income_source, name='edit_income_source'),
    path('settings/income-sources/<int:source_id>/delete/', views.delete_income_source, name='delete_income_source'),
    
    # Expense Categories URLs
    path('settings/expense-categories/add/', views.add_expense_category, name='add_expense_category'),
    path('settings/expense-categories/', views.view_expense_categories, name='view_expense_categories'),
    path('settings/expense-categories/<int:category_id>/edit/', views.edit_expense_category, name='edit_expense_category'),
    path('settings/expense-categories/<int:category_id>/delete/', views.delete_expense_category, name='delete_expense_category'),
    
    # Asset Categories URLs
    path('settings/asset-categories/add/', views.add_asset_category, name='add_asset_category'),
    path('settings/asset-categories/', views.view_asset_categories, name='view_asset_categories'),
    path('settings/asset-categories/<int:category_id>/edit/', views.edit_asset_category, name='edit_asset_category'),
    path('settings/asset-categories/<int:category_id>/delete/', views.delete_asset_category, name='delete_asset_category'),
    
    # Bank Accounts URLs
    path('settings/bank-accounts/add/', views.add_bank_account, name='add_bank_account'),
    path('settings/bank-accounts/', views.view_bank_accounts, name='view_bank_accounts'),
    path('settings/bank-accounts/<int:account_id>/edit/', views.edit_bank_account, name='edit_bank_account'),
    path('settings/bank-accounts/<int:account_id>/delete/', views.delete_bank_account, name='delete_bank_account'),

    # Test URL
    path('test-dropdown/', views.test_dropdown, name='test_dropdown'),
]


