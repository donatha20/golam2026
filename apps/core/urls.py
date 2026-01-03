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
    path('settings/company/', views.company_profile, name='company_profile'),
    path('settings/branches/', views.branch_management, name='branch_management'),
    path('settings/loan-categories/', views.loan_categories, name='loan_categories'),
    path('settings/penalties/', views.penalty_configurations, name='penalty_configurations'),

    # Test URL
    path('test-dropdown/', views.test_dropdown, name='test_dropdown'),
]
