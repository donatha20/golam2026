"""
URL patterns for borrower management.
"""
from django.urls import path
from . import views

app_name = 'borrowers'

urlpatterns = [
    # Borrower/Client Management
    path('', views.borrower_list, name='borrower_list'),
    path('register/', views.register_borrower, name='register_borrower'),
    path('<int:borrower_id>/view/', views.borrower_detail, name='borrower_detail'),
    path('<int:borrower_id>/edit/', views.borrower_edit, name='borrower_edit'),
    path('registration-report/', views.registration_report, name='registration_report'),
    path('without-loans/', views.borrowers_without_loans, name='borrowers_without_loans'),

    # Group Management
    path('groups/', views.group_list, name='group_list'),
    path('groups/register/', views.register_group, name='register_group'),
]
