"""
SMS Management Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import json

from apps.core.models import SMSLog
from apps.core.sms_service import sms_service
from apps.borrowers.models import Borrower
from apps.loans.models import Loan
from apps.repayments.models import Payment
from apps.savings.models import SavingsAccount
from apps.accounts.models import UserRole
from .forms import SendSMSForm, BulkSMSForm


def _require_elevated_sms_access(request, json_response=False):
    if request.user.role in {UserRole.ADMIN, UserRole.MANAGER}:
        return None

    message = 'Only admin and manager users can access SMS management.'
    if json_response:
        return JsonResponse({'success': False, 'message': message}, status=403)

    messages.error(request, message)
    return redirect('core:dashboard')


@login_required
def sms_dashboard(request):
    """SMS dashboard with statistics and recent activity."""
    denied_response = _require_elevated_sms_access(request)
    if denied_response:
        return denied_response
    
    # Get date range for statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # SMS Statistics
    total_sms = SMSLog.objects.count()
    sent_today = SMSLog.objects.filter(sent_at__date=today).count()
    sent_this_week = SMSLog.objects.filter(sent_at__date__gte=week_ago).count()
    sent_this_month = SMSLog.objects.filter(sent_at__date__gte=month_ago).count()
    
    # Status breakdown
    status_stats = SMSLog.objects.values('status').annotate(count=Count('id'))
    
    # Template usage
    template_stats = SMSLog.objects.exclude(
        template_name__isnull=True
    ).values('template_name').annotate(count=Count('id')).order_by('-count')[:5]
    
    # Recent SMS logs
    recent_sms = SMSLog.objects.select_related().order_by('-sent_at')[:10]
    
    # Provider statistics
    provider_stats = SMSLog.objects.values('provider').annotate(count=Count('id'))
    
    context = {
        'total_sms': total_sms,
        'sent_today': sent_today,
        'sent_this_week': sent_this_week,
        'sent_this_month': sent_this_month,
        'status_stats': status_stats,
        'template_stats': template_stats,
        'recent_sms': recent_sms,
        'provider_stats': provider_stats,
        'sms_enabled': sms_service.enabled,
        'current_provider': sms_service.provider,
    }
    
    return render(request, 'sms/dashboard.html', context)


@login_required
def sms_logs(request):
    """View SMS logs with filtering and pagination."""
    denied_response = _require_elevated_sms_access(request)
    if denied_response:
        return denied_response
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    template_filter = request.GET.get('template', '')
    phone_filter = request.GET.get('phone', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    queryset = SMSLog.objects.all()
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if template_filter:
        queryset = queryset.filter(template_name=template_filter)
    
    if phone_filter:
        queryset = queryset.filter(phone_number__icontains=phone_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            queryset = queryset.filter(sent_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            queryset = queryset.filter(sent_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by most recent
    queryset = queryset.order_by('-sent_at')
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    sms_logs = paginator.get_page(page_number)
    
    # Get unique templates for filter dropdown
    templates = SMSLog.objects.exclude(
        template_name__isnull=True
    ).values_list('template_name', flat=True).distinct()
    
    context = {
        'sms_logs': sms_logs,
        'templates': templates,
        'status_filter': status_filter,
        'template_filter': template_filter,
        'phone_filter': phone_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'sms/logs.html', context)


@login_required
def send_sms(request):
    """Send individual SMS."""
    denied_response = _require_elevated_sms_access(request)
    if denied_response:
        return denied_response
    
    if request.method == 'POST':
        form = SendSMSForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            message = form.cleaned_data['message']
            
            # Send SMS
            result = sms_service.send_sms(phone_number, message, template_name='manual')
            
            if result.get('success'):
                messages.success(request, f'SMS sent successfully to {phone_number}')
            else:
                messages.error(request, f'Failed to send SMS: {result.get("error", "Unknown error")}')
            
            return redirect('sms:send_sms')
    else:
        form = SendSMSForm()
    
    context = {
        'form': form,
        'sms_enabled': sms_service.enabled,
        'current_provider': sms_service.provider,
    }
    
    return render(request, 'sms/send_sms.html', context)


@login_required
def bulk_sms(request):
    """Send bulk SMS to multiple recipients."""
    denied_response = _require_elevated_sms_access(request)
    if denied_response:
        return denied_response
    
    if request.method == 'POST':
        form = BulkSMSForm(request.POST)
        if form.is_valid():
            recipient_type = form.cleaned_data['recipient_type']
            message = form.cleaned_data['message']
            
            # Get recipients based on type
            recipients = []
            
            if recipient_type == 'all_borrowers':
                borrowers = Borrower.objects.exclude(phone_number__isnull=True).exclude(phone_number='')
                recipients = [(b.phone_number, b.get_full_name()) for b in borrowers]
            
            elif recipient_type == 'active_borrowers':
                borrowers = Borrower.objects.filter(
                    loans__status='active'
                ).exclude(phone_number__isnull=True).exclude(phone_number='').distinct()
                recipients = [(b.phone_number, b.get_full_name()) for b in borrowers]
            
            elif recipient_type == 'overdue_borrowers':
                # Get borrowers with overdue loans
                overdue_loans = Loan.objects.overdue()
                borrowers = Borrower.objects.filter(
                    loans__in=overdue_loans
                ).exclude(phone_number__isnull=True).exclude(phone_number='').distinct()
                recipients = [(b.phone_number, b.get_full_name()) for b in borrowers]
            
            # Send SMS to all recipients
            sent_count = 0
            failed_count = 0
            
            for phone_number, name in recipients:
                personalized_message = message.replace('{name}', name)
                result = sms_service.send_sms(
                    phone_number, 
                    personalized_message, 
                    template_name='bulk_manual'
                )
                
                if result.get('success'):
                    sent_count += 1
                else:
                    failed_count += 1
            
            messages.success(
                request, 
                f'Bulk SMS completed. Sent: {sent_count}, Failed: {failed_count}'
            )
            
            return redirect('sms:bulk_sms')
    else:
        form = BulkSMSForm()
    
    # Get recipient counts for display
    all_borrowers_count = Borrower.objects.exclude(
        phone_number__isnull=True
    ).exclude(phone_number='').count()
    
    active_borrowers_count = Borrower.objects.filter(
        loans__status='active'
    ).exclude(phone_number__isnull=True).exclude(phone_number='').distinct().count()
    
    overdue_loans = Loan.objects.overdue()
    overdue_borrowers_count = Borrower.objects.filter(
        loans__in=overdue_loans
    ).exclude(phone_number__isnull=True).exclude(phone_number='').distinct().count()
    
    context = {
        'form': form,
        'all_borrowers_count': all_borrowers_count,
        'active_borrowers_count': active_borrowers_count,
        'overdue_borrowers_count': overdue_borrowers_count,
        'sms_enabled': sms_service.enabled,
        'current_provider': sms_service.provider,
    }
    
    return render(request, 'sms/bulk_sms.html', context)


@login_required
def sms_templates(request):
    """Manage SMS templates."""
    denied_response = _require_elevated_sms_access(request)
    if denied_response:
        return denied_response
    
    # Get template usage statistics
    template_stats = SMSLog.objects.exclude(
        template_name__isnull=True
    ).values('template_name').annotate(count=Count('id')).order_by('-count')
    
    context = {
        'template_stats': template_stats,
    }
    
    return render(request, 'sms/templates.html', context)


@login_required
def test_sms(request):
    """Test SMS functionality."""
    denied_response = _require_elevated_sms_access(request, json_response=True)
    if denied_response:
        return denied_response
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        
        if phone_number:
            test_message = f"Test SMS from {sms_service.provider} provider. Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            result = sms_service.send_sms(phone_number, test_message, template_name='test')
            
            return JsonResponse({
                'success': result.get('success', False),
                'message': result.get('error', 'SMS sent successfully') if not result.get('success') else 'Test SMS sent successfully',
                'provider': result.get('provider', sms_service.provider),
                'details': result
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def sms_settings(request):
    """SMS settings and configuration."""
    denied_response = _require_elevated_sms_access(request)
    if denied_response:
        return denied_response
    
    context = {
        'sms_enabled': sms_service.enabled,
        'current_provider': sms_service.provider,
        'available_providers': ['twilio', 'textlocal', 'msg91', 'dummy'],
    }
    
    return render(request, 'sms/settings.html', context)


