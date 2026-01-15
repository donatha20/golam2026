"""
URL configuration for     # Authentication - using registration templates
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/?logout=success', http_method_names=['get', 'post']), name='logout'),
    path('register/', core_views.register, name='register'),ofinance_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.core import views as core_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication - using registration templates
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/?logout=success', http_method_names=['get', 'post']), name='logout'),
    path('register/', core_views.register, name='register'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Core (Dashboard)
    path('', include('apps.core.urls')),

    # Apps
    path('accounts/', include('apps.accounts.urls')),
    path('assets/', include('apps.assets.urls')),
    path('borrowers/', include('apps.borrowers.urls')),
    path('finance/', include('apps.finance_tracker.urls')),
    path('financial-statements/', include('apps.financial_statements.urls')),
    path('loans/', include('apps.loans.urls')),
    path('payroll/', include('apps.payroll.urls')),
    path('repayments/', include('apps.repayments.urls')),
    path('savings/', include('apps.savings.urls')),
    path('sms/', include('apps.sms.urls')),
]

# Serve media files in development
#if settings.DEBUG:
#    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
#
#    # Django Debug Toolbar
#   try:
#        import debug_toolbar
 #       urlpatterns = [
  #          path('__debug__/', include(debug_toolbar.urls)),
   #     ] + urlpatterns
    #except ImportError:
     #   # Debug toolbar not installed, skip
      #  pass
