from django.urls import path
from . import views

app_name = 'finance_tracker'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('api/financial-summary/', views.financial_summary_api, name='financial_summary_api'),

    # Income URLs
    path('income/add/', views.add_income, name='add_income'),
    path('income/', views.view_income, name='view_income'),
    path('income/approvals/', views.income_approval_queue, name='income_approval_queue'),
    path('income/<int:income_id>/approve/', views.approve_income, name='approve_income'),
    path('income/<int:income_id>/reject/', views.reject_income, name='reject_income'),

    # Expenditure URLs
    path('expenditure/add/', views.add_expenditure, name='add_expenditure'),
    path('expenditures/', views.view_expenditures, name='view_expenditures'),
    path('expenditure/approvals/', views.expenditure_approval_queue, name='expenditure_approval_queue'),
    path('expenditure/<int:expenditure_id>/approve/', views.approve_expenditure, name='approve_expenditure'),
    path('expenditure/<int:expenditure_id>/reject/', views.reject_expenditure, name='reject_expenditure'),

    # Category Management URLs
    path('categories/income/', views.manage_income_categories, name='manage_income_categories'),
    path('categories/expenditure/', views.manage_expenditure_categories, name='manage_expenditure_categories'),

    # Capital Management URLs
    path('shareholders/', views.shareholder_list, name='shareholder_list'),
    path('shareholders/add/', views.add_shareholder, name='add_shareholder'),
    path('capital/', views.capital_list, name='capital_list'),
    path('capital/add/', views.add_capital, name='add_capital'),
    path('capital/withdraw/', views.withdraw_capital, name='withdraw_capital'),
    
    # Capital Approval URLs
    path('capital/approvals/', views.capital_approval_list, name='capital_approval_list'),
    path('capital/<int:capital_id>/approve/', views.approve_capital, name='approve_capital'),
    path('capital/<int:capital_id>/detail/', views.capital_approval_detail, name='capital_approval_detail'),
    
    # Financial Analysis URLs
    path('retained-earnings/', views.retained_earnings, name='retained_earnings'),
    path('api/retained-earnings/', views.retained_earnings_api, name='retained_earnings_api'),
]
