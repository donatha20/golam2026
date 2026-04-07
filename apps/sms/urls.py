"""
SMS Management URLs
"""
from django.urls import path
from . import views

app_name = 'sms'

urlpatterns = [
    # Dashboard
    path('', views.sms_dashboard, name='dashboard'),
    
    # SMS Logs
    path('logs/', views.sms_logs, name='logs'),
    
    # Send SMS
    path('send/', views.send_sms, name='send_sms'),
    path('bulk/', views.bulk_sms, name='bulk_sms'),
    
    # Templates
    path('templates/', views.sms_templates, name='templates'),
    
    # Settings & Testing
    path('settings/', views.sms_settings, name='settings'),
    path('test/', views.test_sms, name='test_sms'),
]


