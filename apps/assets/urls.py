"""
URL patterns for assets and collateral management.
"""
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Assets
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/add/', views.add_asset, name='add_asset'),
    path('assets/<int:asset_id>/', views.asset_detail, name='asset_detail'),
    path('assets/reports/', views.asset_reports, name='asset_reports'),
    
    # Collaterals
    path('collaterals/', views.collateral_list, name='collateral_list'),
    path('collaterals/add/', views.add_collateral, name='add_collateral'),
    path('collaterals/<int:collateral_id>/', views.collateral_detail, name='collateral_detail'),
    path('collaterals/reports/', views.collateral_reports, name='collateral_reports'),
]


