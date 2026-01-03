"""
URL configuration for accounts app.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Account Settings
    path('settings/', views.account_settings, name='account_settings'),
    
    # User management (admin only)
    path('users/', views.user_management, name='user_management'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    
    # Branch management (admin only)
    path('branches/', views.branch_management, name='branch_management'),
    path('branches/create/', views.create_branch, name='create_branch'),
    
    # Activity logs (admin only)
    path('activity-log/', views.user_activity_log, name='activity_log'),
]
