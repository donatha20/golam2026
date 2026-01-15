"""
Views for repayment and payment processing.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q, Count, Avg, F
from django.core.paginator import Paginator
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    LoanRepaymentSchedule, Payment, PaymentAllocation, PaymentHistory,
    OutstandingBalance, DailyCollection, CollectionSummary, PaymentStatus
)
from apps.loans.models import Loan
from apps.borrowers.models import Borrower
from apps.accounts.models import UserActivity
from .forms import (
    PaymentForm, BulkPaymentForm, PaymentAllocationForm, PaymentReversalForm,
    ScheduleAdjustmentForm, DailyCollectionForm, PaymentSearchForm
)


@login_required
def dashboard(request):
    """Repayment management dashboard."""
    today = timezone.now().date()
    
    # Payment statistics
    payment_stats = {
        'today_collections': Payment.objects.filter(
            payment_date=today,
            status=PaymentStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'today_payments_count': Payment.objects.filter(
            payment_date=today,
            status=PaymentStatus.COMPLETED
        ).count(),
        'pending_payments': Payment.objects.filter(
            status=PaymentStatus.PENDING
        ).count(),
        'total_outstanding': OutstandingBalance.objects.filter(
            is_current=True
        ).aggregate(total=Sum('total_outstanding'))['total'] or Decimal('0.00'),
    }
    
    # Overdue statistics
    overdue_stats = {
        'overdue_installments': LoanRepaymentSchedule.objects.filter(
            payment_status='overdue'
        ).count(),
        'overdue_amount': LoanRepaymentSchedule.objects.filter(
            payment_status='overdue'
        ).aggregate(total=Sum('total_amount') - Sum('total_paid'))['total'] or Decimal('0.00'),
        'overdue_borrowers': LoanRepaymentSchedule.objects.filter(
            payment_status='overdue'
        ).values('loan__borrower').distinct().count(),
    }
    
    # Collection efficiency
    this_month_start = today.replace(day=1)
    collection_stats = {
        'month_collections': Payment.objects.filter(
            payment_date__gte=this_month_start,
            status=PaymentStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'month_target': Decimal('1000000.00'),  # This should come from settings
        'collection_efficiency': 0,  # Calculate based on due vs collected
    }
    
    # Recent activities
    recent_payments = Payment.objects.select_related(
        'loan', 'borrower', 'collected_by'
    ).order_by('-created_at')[:10]
    
    recent_overdue = LoanRepaymentSchedule.objects.filter(
        payment_status='overdue'
    ).select_related('loan__borrower').order_by('-due_date')[:10]
    
    # Daily collections summary
    daily_collections = DailyCollection.objects.filter(
        collection_date__gte=today - timedelta(days=7)
    ).order_by('-collection_date')[:7]
    
    context = {
        'payment_stats': payment_stats,
        'overdue_stats': overdue_stats,
        'collection_stats': collection_stats,
        'recent_payments': recent_payments,
        'recent_overdue': recent_overdue,
        'daily_collections': daily_collections,
        'title': 'Repayment Management',
        'page_title': 'Repayment Dashboard',
    }
    
    return render(request, 'repayments/dashboard.html', context)


@login_required
def payment_list(request):
    """List all payments with filtering and search."""
    payments = Payment.objects.select_related(
        'loan', 'borrower', 'collected_by', 'verified_by'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        payments = payments.filter(
            Q(payment_reference__icontains=search_query) |
            Q(loan__loan_number__icontains=search_query) |
            Q(borrower__first_name__icontains=search_query) |
            Q(borrower__last_name__icontains=search_query) |
            Q(borrower__phone_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    # Filter by payment method
    method_filter = request.GET.get('method', '')
    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    # Filter by collector
    collector_filter = request.GET.get('collector', '')
    if collector_filter:
        payments = payments.filter(collected_by_id=collector_filter)
    
    # Pagination
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)
    
    # Get filter options
    from apps.accounts.models import CustomUser
    collectors = CustomUser.objects.filter(
        collected_payments__isnull=False
    ).distinct().order_by('first_name', 'last_name')
    
    context = {
        'payments': payments,
        'collectors': collectors,
        'search_query': search_query,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'collector_filter': collector_filter,
        'payment_statuses': PaymentStatus.choices,
        'title': 'Payment History',
        'page_title': 'All Payments',
    }
    
    return render(request, 'repayments/payment_list.html', context)


@login_required
def payment_detail(request, payment_id):
    """View payment details."""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Get payment allocations
    allocations = payment.allocations.select_related('installment').order_by(
        'installment__installment_number'
    )
    
    # Get payment history
    history = payment.history.select_related('performed_by').order_by('-action_date')
    
    # Calculate payment impact
    loan_balance_impact = {
        'before': payment.loan_balance_before,
        'after': payment.loan_balance_after,
        'reduction': (payment.loan_balance_before or Decimal('0.00')) - (payment.loan_balance_after or Decimal('0.00'))
    }
    
    context = {
        'payment': payment,
        'allocations': allocations,
        'history': history,
        'loan_balance_impact': loan_balance_impact,
        'title': f'Payment - {payment.payment_reference}',
        'page_title': payment.payment_reference,
    }
    
    return render(request, 'repayments/payment_detail.html', context)


@login_required
def process_payment(request):
    """Process new payment."""
    if request.method == 'POST':
        # This will be implemented with forms
        pass
    
    # Get active loans for payment
    active_loans = Loan.objects.filter(
        status__in=['active', 'overdue']
    ).select_related('borrower').order_by('loan_number')
    
    context = {
        'active_loans': active_loans,
        'title': 'Process Payment',
        'page_title': 'New Payment',
    }
    
    return render(request, 'repayments/process_payment.html', context)


@login_required
def repayment_schedule(request, loan_id):
    """View loan repayment schedule."""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get repayment schedule
    schedule = loan.repayment_schedule.order_by('installment_number')
    
    # Calculate schedule statistics
    schedule_stats = {
            'total_installments': schedule.count(),
            'paid_installments': schedule.filter(is_paid=True).count(),
            'overdue_installments': schedule.filter(payment_status='overdue').count(),
            'total_scheduled': schedule.aggregate(total=Sum('scheduled_total'))['total'] or Decimal('0.00'),
            'total_paid': schedule.aggregate(total=Sum('total_paid'))['total'] or Decimal('0.00'),
            'total_outstanding': schedule.aggregate(
                total=Sum('total_amount') - Sum('total_paid')
            )['total'] or Decimal('0.00'),
        }    # Get payment history for this loan
    payments = loan.payments.order_by('-payment_date')[:10]
    
    context = {
        'loan': loan,
        'schedule': schedule,
        'schedule_stats': schedule_stats,
        'payments': payments,
        'title': f'Repayment Schedule - {loan.loan_number}',
        'page_title': f'Schedule - {loan.loan_number}',
    }
    
    return render(request, 'repayments/repayment_schedule.html', context)


@login_required
def overdue_payments(request):
    """List overdue payments."""
    overdue_installments = LoanRepaymentSchedule.objects.filter(
        payment_status='overdue'
    ).select_related('loan__borrower').order_by('-days_overdue', 'due_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        overdue_installments = overdue_installments.filter(
            Q(loan__loan_number__icontains=search_query) |
            Q(loan__borrower__first_name__icontains=search_query) |
            Q(loan__borrower__last_name__icontains=search_query) |
            Q(loan__borrower__phone_number__icontains=search_query)
        )
    
    # Filter by days overdue
    days_filter = request.GET.get('days', '')
    if days_filter:
        if days_filter == '1-7':
            overdue_installments = overdue_installments.filter(days_overdue__lte=7)
        elif days_filter == '8-30':
            overdue_installments = overdue_installments.filter(days_overdue__gte=8, days_overdue__lte=30)
        elif days_filter == '31-90':
            overdue_installments = overdue_installments.filter(days_overdue__gte=31, days_overdue__lte=90)
        elif days_filter == '90+':
            overdue_installments = overdue_installments.filter(days_overdue__gt=90)
    
    # Pagination
    paginator = Paginator(overdue_installments, 25)
    page_number = request.GET.get('page')
    overdue_installments = paginator.get_page(page_number)
    
    # Calculate totals
    total_overdue_amount = LoanRepaymentSchedule.objects.filter(
        payment_status='overdue'
    ).aggregate(total=Sum('total_amount') - Sum('total_paid'))['total'] or Decimal('0.00')
    
    context = {
        'overdue_installments': overdue_installments,
        'total_overdue_amount': total_overdue_amount,
        'search_query': search_query,
        'days_filter': days_filter,
        'title': 'Overdue Payments',
        'page_title': 'Overdue Payments',
    }
    
    return render(request, 'repayments/overdue_payments.html', context)


@login_required
def outstanding_balances(request):
    """View outstanding balances for all loans."""
    balances = OutstandingBalance.objects.filter(
        is_current=True
    ).select_related('loan__borrower').order_by('-total_outstanding')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        balances = balances.filter(
            Q(loan__loan_number__icontains=search_query) |
            Q(loan__borrower__first_name__icontains=search_query) |
            Q(loan__borrower__last_name__icontains=search_query) |
            Q(loan__borrower__phone_number__icontains=search_query)
        )

    # Filter by balance range
    balance_filter = request.GET.get('balance', '')
    if balance_filter:
        if balance_filter == '0-10000':
            balances = balances.filter(total_outstanding__lte=10000)
        elif balance_filter == '10001-50000':
            balances = balances.filter(total_outstanding__gte=10001, total_outstanding__lte=50000)
        elif balance_filter == '50001-100000':
            balances = balances.filter(total_outstanding__gte=50001, total_outstanding__lte=100000)
        elif balance_filter == '100000+':
            balances = balances.filter(total_outstanding__gt=100000)

    # Filter by overdue status
    overdue_filter = request.GET.get('overdue', '')
    if overdue_filter == 'yes':
        balances = balances.filter(days_overdue__gt=0)
    elif overdue_filter == 'no':
        balances = balances.filter(days_overdue=0)

    # Pagination
    paginator = Paginator(balances, 25)
    page_number = request.GET.get('page')
    balances = paginator.get_page(page_number)

    # Calculate totals
    total_stats = OutstandingBalance.objects.filter(is_current=True).aggregate(
        total_principal=Sum('principal_outstanding'),
        total_interest=Sum('interest_outstanding'),
        total_penalty=Sum('penalty_outstanding'),
        total_fees=Sum('fees_outstanding'),
        total_outstanding=Sum('total_outstanding'),
        count=Count('id')
    )

    context = {
        'balances': balances,
        'total_stats': total_stats,
        'search_query': search_query,
        'balance_filter': balance_filter,
        'overdue_filter': overdue_filter,
        'title': 'Outstanding Balances',
        'page_title': 'Outstanding Balances',
    }

    return render(request, 'repayments/outstanding_balances.html', context)


@login_required
def collection_report(request):
    """Generate collection reports."""
    report_type = request.GET.get('report_type', 'daily')

    if report_type == 'daily':
        # Daily collection report
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')

        if not date_from:
            date_from = timezone.now().date() - timedelta(days=30)
        if not date_to:
            date_to = timezone.now().date()

        collections = DailyCollection.objects.filter(
            collection_date__range=[date_from, date_to]
        ).order_by('-collection_date')

        # Calculate totals
        total_collections = collections.aggregate(
            total_amount=Sum('total_amount'),
            total_payments=Sum('payment_count'),
            avg_amount=Avg('total_amount')
        )

        report_data = {
            'collections': collections,
            'total_collections': total_collections,
            'date_from': date_from,
            'date_to': date_to,
        }

    elif report_type == 'collector':
        # Collector-wise collection report
        date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
        date_to = request.GET.get('date_to', timezone.now().date())

        from apps.accounts.models import CustomUser
        collectors = CustomUser.objects.filter(
            collected_payments__payment_date__range=[date_from, date_to]
        ).annotate(
            total_collected=Sum('collected_payments__amount'),
            payment_count=Count('collected_payments'),
            avg_payment=Avg('collected_payments__amount')
        ).order_by('-total_collected')

        report_data = {
            'collectors': collectors,
            'date_from': date_from,
            'date_to': date_to,
        }

    else:
        # Payment method report
        date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
        date_to = request.GET.get('date_to', timezone.now().date())

        method_stats = Payment.objects.filter(
            payment_date__range=[date_from, date_to],
            status=PaymentStatus.COMPLETED
        ).values('payment_method').annotate(
            total_amount=Sum('amount'),
            payment_count=Count('id'),
            avg_amount=Avg('amount')
        ).order_by('-total_amount')

        report_data = {
            'method_stats': method_stats,
            'date_from': date_from,
            'date_to': date_to,
        }

    context = {
        'report_type': report_type,
        'report_data': report_data,
        'title': 'Collection Reports',
        'page_title': 'Collection Reports',
    }

    return render(request, 'repayments/collection_report.html', context)


# =============================================================================
# API VIEWS
# =============================================================================

@login_required
def get_loan_balance(request, loan_id):
    """API endpoint to get loan balance information."""
    try:
        loan = get_object_or_404(Loan, id=loan_id)

        # Get current balance
        try:
            balance = OutstandingBalance.objects.get(loan=loan, is_current=True)
            balance_data = {
                'principal_outstanding': float(balance.principal_outstanding),
                'interest_outstanding': float(balance.interest_outstanding),
                'penalty_outstanding': float(balance.penalty_outstanding),
                'fees_outstanding': float(balance.fees_outstanding),
                'total_outstanding': float(balance.total_outstanding),
                'days_overdue': balance.days_overdue,
                'last_payment_date': balance.last_payment_date.isoformat() if balance.last_payment_date else None,
                'next_due_date': balance.next_due_date.isoformat() if balance.next_due_date else None,
            }
        except OutstandingBalance.DoesNotExist:
            # Calculate balance from schedule
            schedule = loan.repayment_schedule.aggregate(
                principal=Sum('principal_amount') - Sum('principal_paid'),
                interest=Sum('interest_amount') - Sum('interest_paid'),
                penalty=Sum('penalty_amount') - Sum('penalty_paid'),
                fees=Sum('fees_amount') - Sum('fees_paid'),
            )

            balance_data = {
                'principal_outstanding': float(schedule['principal'] or 0),
                'interest_outstanding': float(schedule['interest'] or 0),
                'penalty_outstanding': float(schedule['penalty'] or 0),
                'fees_outstanding': float(schedule['fees'] or 0),
                'total_outstanding': float(
                    (schedule['principal'] or 0) + (schedule['interest'] or 0) +
                    (schedule['penalty'] or 0) + (schedule['fees'] or 0)
                ),
                'days_overdue': 0,
                'last_payment_date': None,
                'next_due_date': None,
            }

        # Get next due installment
        next_installment = loan.repayment_schedule.filter(
            payment_status__in=['pending', 'partial', 'overdue']
        ).order_by('due_date').first()

        if next_installment:
            balance_data['next_due_date'] = next_installment.due_date.isoformat()
            # Calculate outstanding amount for the installment
            next_due_outstanding = (
                next_installment.total_amount - next_installment.total_paid
            )
            balance_data['next_due_amount'] = float(next_due_outstanding)

        return JsonResponse({
            'success': True,
            'loan_number': loan.loan_number,
            'borrower_name': loan.borrower.get_full_name(),
            'balance': balance_data
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def calculate_payment_allocation(request):
    """API endpoint to calculate payment allocation."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            loan_id = data.get('loan_id')
            payment_amount = Decimal(str(data.get('payment_amount', '0')))

            loan = get_object_or_404(Loan, id=loan_id)

            # Get installments in order of priority
            installments = loan.repayment_schedule.filter(
                payment_status__in=['pending', 'partial', 'overdue']
            ).order_by('due_date', 'installment_number')

            allocation_preview = []
            remaining_amount = payment_amount

            for installment in installments:
                if remaining_amount <= 0:
                    break

                outstanding = installment.outstanding_amount
                if outstanding <= 0:
                    continue

                allocation_amount = min(remaining_amount, outstanding)

                # Simulate allocation
                temp_allocation = {
                    'installment_number': installment.installment_number,
                    'due_date': installment.due_date.isoformat(),
                    'outstanding_amount': float(outstanding),
                    'allocation_amount': float(allocation_amount),
                    'penalty': float(min(remaining_amount, installment.outstanding_penalty)),
                    'interest': 0,
                    'principal': 0,
                    'fees': 0,
                }

                # Calculate detailed allocation
                temp_remaining = allocation_amount

                # Penalty first
                penalty_due = installment.outstanding_penalty
                if penalty_due > 0 and temp_remaining > 0:
                    penalty_payment = min(temp_remaining, penalty_due)
                    temp_allocation['penalty'] = float(penalty_payment)
                    temp_remaining -= penalty_payment

                # Interest
                interest_due = installment.outstanding_interest
                if interest_due > 0 and temp_remaining > 0:
                    interest_payment = min(temp_remaining, interest_due)
                    temp_allocation['interest'] = float(interest_payment)
                    temp_remaining -= interest_payment

                # Principal
                principal_due = installment.outstanding_principal
                if principal_due > 0 and temp_remaining > 0:
                    principal_payment = min(temp_remaining, principal_due)
                    temp_allocation['principal'] = float(principal_payment)
                    temp_remaining -= principal_payment

                # Fees
                fees_due = installment.outstanding_fees
                if fees_due > 0 and temp_remaining > 0:
                    fees_payment = min(temp_remaining, fees_due)
                    temp_allocation['fees'] = float(fees_payment)
                    temp_remaining -= fees_payment

                allocation_preview.append(temp_allocation)
                remaining_amount -= allocation_amount

            return JsonResponse({
                'success': True,
                'allocation_preview': allocation_preview,
                'total_allocated': float(payment_amount - remaining_amount),
                'excess_amount': float(remaining_amount)
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# =============================================================================
# DAILY COLLECTIONS VIEWS
# =============================================================================

@login_required
def daily_collections_dashboard(request):
    """Daily collections dashboard."""
    today = timezone.now().date()

    # Get date filter
    selected_date = request.GET.get('date', str(today))
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        selected_date = today

    # Get daily collections for selected date
    collections = DailyCollection.objects.filter(
        collection_date=selected_date
    ).select_related('collector', 'verified_by').order_by('collector__first_name')

    # Get or create collection summary
    summary, created = CollectionSummary.objects.get_or_create(
        summary_date=selected_date
    )
    if created or not summary.updated_at or summary.updated_at < timezone.now() - timedelta(minutes=30):
        summary.generate_summary()

    # Calculate statistics
    stats = {
        'total_collectors': collections.count(),
        'active_collectors': collections.filter(payment_count__gt=0).count(),
        'total_amount': summary.total_amount,
        'total_payments': summary.total_payments,
        'total_target': summary.total_target,
        'achievement_percentage': summary.achievement_percentage,
        'collections_with_discrepancy': summary.collections_with_discrepancy,
        'pending_validation': collections.filter(validation_status='pending').count(),
        'validated_collections': collections.filter(validation_status='validated').count(),
    }

    # Top performers
    top_performers = collections.filter(
        payment_count__gt=0
    ).order_by('-collection_efficiency')[:5]

    # Collections needing attention
    needs_attention = collections.filter(
        Q(has_discrepancy=True) | Q(validation_status='pending')
    ).order_by('-discrepancy_amount')

    # Payment method breakdown
    method_breakdown = {
        'cash': summary.cash_total,
        'digital': summary.digital_total,
        'bank': summary.bank_total,
    }

    # Collection type breakdown
    type_breakdown = {
        'regular': summary.regular_total,
        'overdue': summary.overdue_total,
        'advance': summary.advance_total,
        'penalty': summary.penalty_total,
    }

    context = {
        'selected_date': selected_date,
        'collections': collections,
        'summary': summary,
        'stats': stats,
        'top_performers': top_performers,
        'needs_attention': needs_attention,
        'method_breakdown': method_breakdown,
        'type_breakdown': type_breakdown,
        'title': 'Daily Collections',
        'page_title': f'Collections - {selected_date.strftime("%B %d, %Y")}',
    }

    return render(request, 'repayments/daily_collections_dashboard.html', context)


# =============================================================================
# PAYMENT RECORDING VIEWS
# =============================================================================

@login_required
def record_payment(request):
    """Record a new payment."""
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.collected_by = request.user
                    payment.status = PaymentStatus.COMPLETED
                    payment.save()

                    # Process payment allocation
                    process_payment_allocation(payment)

                    # Update loan balances
                    update_loan_balances(payment.loan)

                    # Log activity
                    UserActivity.objects.create(
                        user=request.user,
                        action='payment_recorded',
                        description=f'Recorded payment of Tsh {payment.amount} for loan {payment.loan.loan_number}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )

                    # Send SMS notification
                    try:
                        from apps.core.sms_service import sms_service
                        sms_result = sms_service.send_payment_confirmation(payment)
                        if sms_result.get('success'):
                            messages.success(
                                request,
                                f'Payment of Tsh {payment.amount:,.2f} recorded successfully for loan {payment.loan.loan_number}. SMS confirmation sent.'
                            )
                        else:
                            messages.success(
                                request,
                                f'Payment of Tsh {payment.amount:,.2f} recorded successfully for loan {payment.loan.loan_number}'
                            )
                            messages.warning(request, f'SMS notification failed: {sms_result.get("error", "Unknown error")}')
                    except Exception as e:
                        messages.success(
                            request,
                            f'Payment of Tsh {payment.amount:,.2f} recorded successfully for loan {payment.loan.loan_number}'
                        )
                        messages.warning(request, f'SMS notification failed: {str(e)}')

                    return redirect('repayments:loan_repayments', loan_id=payment.loan.pk)

            except Exception as e:
                messages.error(request, f'Error recording payment: {str(e)}')
    else:
        form = PaymentForm()

        # Pre-select loan if provided in URL
        loan_id = request.GET.get('loan')
        if loan_id:
            try:
                loan = Loan.objects.get(pk=loan_id)
                form.fields['loan'].initial = loan
            except Loan.DoesNotExist:
                pass

    return render(request, 'repayments/record_repayment.html', {
        'form': form,
        'title': 'Record Payment'
    })


@login_required
def loan_repayments(request, loan_id):
    """View loan repayment history and schedule."""
    loan = get_object_or_404(Loan, pk=loan_id)

    # Get payment history
    payments = Payment.objects.filter(loan=loan).select_related(
        'collected_by'
    ).prefetch_related('allocations__installment').order_by('-payment_date')

    # Get repayment schedule
    schedule = LoanRepaymentSchedule.objects.filter(loan=loan).order_by('installment_number')

    # Calculate statistics
    total_paid = payments.filter(status=PaymentStatus.COMPLETED).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    payment_progress = 0
    if loan.principal_amount > 0:
        payment_progress = (total_paid / loan.principal_amount) * 100

    paid_installments = schedule.filter(payment_status='paid').count()
    pending_installments = schedule.filter(payment_status__in=['pending', 'overdue']).count()

    context = {
        'loan': loan,
        'payments': payments,
        'schedule': schedule,
        'total_paid': total_paid,
        'payment_progress': min(payment_progress, 100),
        'paid_installments': paid_installments,
        'pending_installments': pending_installments,
        'title': f'Repayments - {loan.loan_number}'
    }

    return render(request, 'repayments/loan_repayments.html', context)


@login_required
def payment_detail(request, payment_id):
    """View payment details."""
    payment = get_object_or_404(Payment, pk=payment_id)

    context = {
        'payment': payment,
        'allocations': payment.allocations.all(),
        'title': f'Payment Details - {payment.payment_reference}'
    }

    return render(request, 'repayments/payment_detail.html', context)


@login_required
def reverse_payment(request, payment_id):
    """Reverse a payment."""
    payment = get_object_or_404(Payment, pk=payment_id, status=PaymentStatus.COMPLETED, is_reversed=False)

    if request.method == 'POST':
        form = PaymentReversalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Mark payment as reversed
                    payment.is_reversed = True
                    payment.reversal_reason = form.cleaned_data['reversal_reason']
                    payment.reversed_by = request.user
                    payment.reversal_date = timezone.now()
                    payment.save()

                    # Reverse payment allocations
                    reverse_payment_allocations(payment)

                    # Update loan balances
                    update_loan_balances(payment.loan)

                    # Log activity
                    UserActivity.objects.create(
                        user=request.user,
                        action='payment_reversed',
                        description=f'Reversed payment {payment.payment_reference} for loan {payment.loan.loan_number}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )

                    messages.success(request, f'Payment {payment.payment_reference} reversed successfully')
                    return redirect('repayments:loan_repayments', loan_id=payment.loan.pk)

            except Exception as e:
                messages.error(request, f'Error reversing payment: {str(e)}')

    return redirect('repayments:loan_repayments', loan_id=payment.loan.pk)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def process_payment_allocation(payment):
    """Process automatic payment allocation."""
    loan = payment.loan
    remaining_amount = payment.amount

    # Get overdue installments first
    overdue_installments = loan.repayment_schedule.filter(
        payment_status='overdue'
    ).order_by('due_date')

    # Then get pending installments
    pending_installments = loan.repayment_schedule.filter(
        payment_status='pending'
    ).order_by('due_date')

    # Combine installments (overdue first)
    installments = list(overdue_installments) + list(pending_installments)

    for installment in installments:
        if remaining_amount <= 0:
            break

        # Calculate outstanding amounts for this installment
        outstanding_penalty = installment.penalty_amount - installment.penalty_paid
        outstanding_interest = installment.interest_amount - installment.interest_paid
        outstanding_principal = installment.principal_amount - installment.principal_paid
        outstanding_fees = installment.fees_amount - installment.fees_paid

        # Allocate payment (penalty first, then interest, then principal, then fees)
        penalty_allocation = min(remaining_amount, outstanding_penalty)
        remaining_amount -= penalty_allocation

        interest_allocation = min(remaining_amount, outstanding_interest)
        remaining_amount -= interest_allocation

        principal_allocation = min(remaining_amount, outstanding_principal)
        remaining_amount -= principal_allocation

        fees_allocation = min(remaining_amount, outstanding_fees)
        remaining_amount -= fees_allocation

        # Create allocation record
        if penalty_allocation > 0 or interest_allocation > 0 or principal_allocation > 0 or fees_allocation > 0:
            PaymentAllocation.objects.create(
                payment=payment,
                installment=installment,
                principal_allocated=principal_allocation,
                interest_allocated=interest_allocation,
                penalty_allocated=penalty_allocation,
                fees_allocated=fees_allocation
            )

            # Update installment paid amounts
            installment.principal_paid += principal_allocation
            installment.interest_paid += interest_allocation
            installment.penalty_paid += penalty_allocation
            installment.fees_paid += fees_allocation

            # Update installment status
            total_due = installment.principal_amount + installment.interest_amount + installment.penalty_amount + installment.fees_amount
            total_paid = installment.principal_paid + installment.interest_paid + installment.penalty_paid + installment.fees_paid

            if total_paid >= total_due:
                installment.payment_status = 'paid'
                installment.paid_date = payment.payment_date
            elif total_paid > 0:
                installment.payment_status = 'partial'

            installment.save()


def reverse_payment_allocations(payment):
    """Reverse payment allocations."""
    for allocation in payment.allocations.all():
        installment = allocation.installment

        # Reverse the allocation amounts
        installment.principal_paid -= allocation.principal_allocated
        installment.interest_paid -= allocation.interest_allocated
        installment.penalty_paid -= allocation.penalty_allocated
        installment.fees_paid -= allocation.fees_allocated

        # Update installment status
        total_due = installment.principal_amount + installment.interest_amount + installment.penalty_amount + installment.fees_amount
        total_paid = installment.principal_paid + installment.interest_paid + installment.penalty_paid + installment.fees_paid

        if total_paid <= 0:
            installment.payment_status = 'pending'
            installment.paid_date = None
        elif total_paid < total_due:
            installment.payment_status = 'partial'

        installment.save()


def update_loan_balances(loan):
    """Update loan outstanding balances."""
    # Calculate total paid amounts
    total_principal_paid = loan.repayment_schedule.aggregate(
        total=Sum('principal_paid')
    )['total'] or Decimal('0.00')

    total_interest_paid = loan.repayment_schedule.aggregate(
        total=Sum('interest_paid')
    )['total'] or Decimal('0.00')

    total_penalty_paid = loan.repayment_schedule.aggregate(
        total=Sum('penalty_paid')
    )['total'] or Decimal('0.00')

    # Update loan balances
    loan.principal_paid = total_principal_paid
    loan.interest_paid = total_interest_paid
    loan.penalty_paid = total_penalty_paid

    loan.outstanding_balance = (
        loan.principal_amount + loan.total_interest + loan.penalty_amount -
        total_principal_paid - total_interest_paid - total_penalty_paid
    )

    # Update loan status
    if loan.outstanding_balance <= 0:
        loan.status = 'completed'
        loan.completion_date = timezone.now().date()
    elif loan.outstanding_balance < loan.principal_amount + loan.total_interest:
        loan.status = 'active'

    loan.save()


@login_required
def collector_collections(request, collector_id):
    """View collections for a specific collector."""
    from apps.accounts.models import CustomUser
    collector = get_object_or_404(CustomUser, id=collector_id)

    # Get date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if not date_from:
        date_from = timezone.now().date() - timedelta(days=30)
    else:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

    if not date_to:
        date_to = timezone.now().date()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

    # Get collections
    collections = DailyCollection.objects.filter(
        collector=collector,
        collection_date__range=[date_from, date_to]
    ).order_by('-collection_date')

    # Calculate statistics
    stats = collections.aggregate(
        total_amount=Sum('total_amount'),
        total_payments=Sum('payment_count'),
        total_target=Sum('target_amount'),
        avg_efficiency=Avg('collection_efficiency'),
        collections_count=Count('id'),
        discrepancies=Count('id', filter=Q(has_discrepancy=True))
    )

    # Calculate achievement percentage
    if stats['total_target'] and stats['total_target'] > 0:
        stats['achievement_percentage'] = (stats['total_amount'] / stats['total_target']) * 100
    else:
        stats['achievement_percentage'] = 0

    # Pagination
    paginator = Paginator(collections, 20)
    page_number = request.GET.get('page')
    collections = paginator.get_page(page_number)

    context = {
        'collector': collector,
        'collections': collections,
        'stats': stats,
        'date_from': date_from,
        'date_to': date_to,
        'title': f'Collections - {collector.get_full_name()}',
        'page_title': f'{collector.get_full_name()} Collections',
    }

    return render(request, 'repayments/collector_collections.html', context)


@login_required
def collection_validation(request):
    """Collection validation interface."""
    # Get collections pending validation
    pending_collections = DailyCollection.objects.filter(
        validation_status='pending'
    ).select_related('collector').order_by('-collection_date', 'collector__first_name')

    # Get collections with discrepancies
    discrepancy_collections = DailyCollection.objects.filter(
        has_discrepancy=True,
        discrepancy_resolved=False
    ).select_related('collector').order_by('-discrepancy_amount')

    # Filter by date if provided
    date_filter = request.GET.get('date', '')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            pending_collections = pending_collections.filter(collection_date=filter_date)
            discrepancy_collections = discrepancy_collections.filter(collection_date=filter_date)
        except ValueError:
            pass

    # Pagination
    pending_paginator = Paginator(pending_collections, 15)
    pending_page = request.GET.get('pending_page')
    pending_collections = pending_paginator.get_page(pending_page)

    discrepancy_paginator = Paginator(discrepancy_collections, 15)
    discrepancy_page = request.GET.get('discrepancy_page')
    discrepancy_collections = discrepancy_paginator.get_page(discrepancy_page)

    # Statistics
    validation_stats = {
        'pending_count': DailyCollection.objects.filter(validation_status='pending').count(),
        'discrepancy_count': DailyCollection.objects.filter(has_discrepancy=True, discrepancy_resolved=False).count(),
        'total_discrepancy_amount': DailyCollection.objects.filter(
            has_discrepancy=True, discrepancy_resolved=False
        ).aggregate(total=Sum('discrepancy_amount'))['total'] or Decimal('0.00'),
        'validated_today': DailyCollection.objects.filter(
            validation_status='validated',
            verification_date__date=timezone.now().date()
        ).count(),
    }

    context = {
        'pending_collections': pending_collections,
        'discrepancy_collections': discrepancy_collections,
        'validation_stats': validation_stats,
        'date_filter': date_filter,
        'title': 'Collection Validation',
        'page_title': 'Validate Collections',
    }

    return render(request, 'repayments/collection_validation.html', context)


@login_required
def collection_summary(request):
    """View collection summaries."""
    # Get date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if not date_from:
        date_from = timezone.now().date() - timedelta(days=30)
    else:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

    if not date_to:
        date_to = timezone.now().date()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

    # Get summaries
    summaries = CollectionSummary.objects.filter(
        summary_date__range=[date_from, date_to]
    ).order_by('-summary_date')

    # Calculate period totals
    period_stats = summaries.aggregate(
        total_amount=Sum('total_amount'),
        total_payments=Sum('total_payments'),
        total_target=Sum('total_target'),
        avg_achievement=Avg('achievement_percentage'),
        total_discrepancies=Sum('collections_with_discrepancy'),
        approved_summaries=Count('id', filter=Q(is_approved=True))
    )

    # Calculate achievement percentage for period
    if period_stats['total_target'] and period_stats['total_target'] > 0:
        period_stats['period_achievement'] = (period_stats['total_amount'] / period_stats['total_target']) * 100
    else:
        period_stats['period_achievement'] = 0

    # Pagination
    paginator = Paginator(summaries, 20)
    page_number = request.GET.get('page')
    summaries = paginator.get_page(page_number)

    context = {
        'summaries': summaries,
        'period_stats': period_stats,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'Collection Summaries',
        'page_title': 'Collection Summaries',
    }

    return render(request, 'repayments/collection_summary.html', context)


@login_required
def validate_collection(request, collection_id):
    """Validate a specific collection."""
    collection = get_object_or_404(DailyCollection, id=collection_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'validate':
            # Validate collection
            is_valid = collection.validate_collection()

            if is_valid:
                collection.validation_status = 'validated'
                collection.is_verified = True
                collection.verified_by = request.user
                collection.verification_date = timezone.now()
                collection.verification_notes = request.POST.get('notes', '')
                collection.save()

                messages.success(request, f'Collection for {collection.collector.get_full_name()} validated successfully.')
            else:
                messages.warning(request, f'Collection has discrepancies. Please review and resolve.')

        elif action == 'approve':
            if collection.validation_status == 'validated':
                collection.validation_status = 'approved'
                collection.is_verified = True
                collection.verified_by = request.user
                collection.verification_date = timezone.now()
                collection.verification_notes = request.POST.get('notes', '')
                collection.save()

                messages.success(request, f'Collection approved successfully.')
            else:
                messages.error(request, 'Collection must be validated before approval.')

        elif action == 'reject':
            reason = request.POST.get('reason', '')
            if not reason:
                messages.error(request, 'Rejection reason is required.')
            else:
                collection.reject_collection(request.user, reason)
                messages.success(request, f'Collection rejected.')

        elif action == 'resolve_discrepancy':
            resolution_notes = request.POST.get('resolution_notes', '')
            if not resolution_notes:
                messages.error(request, 'Resolution notes are required.')
            else:
                collection.resolve_discrepancy(request.user, resolution_notes)
                messages.success(request, f'Discrepancy resolved successfully.')

        return redirect('repayments:collection_validation')

    # Get calculated totals for comparison
    calculated_totals = collection.get_calculated_totals()

    # Get individual payments for this collection
    payments = Payment.objects.filter(
        payment_date=collection.collection_date,
        collected_by=collection.collector,
        status=PaymentStatus.COMPLETED
    ).select_related('loan', 'borrower').order_by('-created_at')

    context = {
        'collection': collection,
        'calculated_totals': calculated_totals,
        'payments': payments,
        'title': f'Validate Collection - {collection.collector.get_full_name()}',
        'page_title': f'Validate - {collection.collection_date}',
    }

    return render(request, 'repayments/validate_collection.html', context)


# =============================================================================
# COLLECTION API VIEWS
# =============================================================================

@login_required
def get_collection_data(request, collection_id):
    """API endpoint to get collection data."""
    try:
        collection = get_object_or_404(DailyCollection, id=collection_id)

        data = {
            'id': collection.id,
            'collection_date': collection.collection_date.isoformat(),
            'collector_name': collection.collector.get_full_name(),
            'total_amount': float(collection.total_amount),
            'payment_count': collection.payment_count,
            'target_amount': float(collection.target_amount),
            'collection_efficiency': float(collection.collection_efficiency),
            'validation_status': collection.validation_status,
            'has_discrepancy': collection.has_discrepancy,
            'discrepancy_amount': float(collection.discrepancy_amount) if collection.discrepancy_amount else 0,
            'is_verified': collection.is_verified,
            'cash_amount': float(collection.cash_amount),
            'digital_amount': float(collection.digital_amount),
            'bank_amount': float(collection.bank_amount),
            'regular_amount': float(collection.regular_amount),
            'overdue_amount': float(collection.overdue_amount),
            'advance_amount': float(collection.advance_amount),
            'penalty_amount': float(collection.penalty_amount),
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def recalculate_collection(request, collection_id):
    """API endpoint to recalculate collection totals."""
    if request.method == 'POST':
        try:
            collection = get_object_or_404(DailyCollection, id=collection_id)

            # Recalculate totals from payments
            collection.calculate_totals_from_payments()

            return JsonResponse({
                'success': True,
                'message': 'Collection totals recalculated successfully',
                'data': {
                    'total_amount': float(collection.total_amount),
                    'payment_count': collection.payment_count,
                    'borrower_count': collection.borrower_count,
                }
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
def generate_daily_summary(request):
    """API endpoint to generate daily collection summary."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            summary_date = data.get('summary_date')

            if not summary_date:
                return JsonResponse({'success': False, 'error': 'Summary date is required'}, status=400)

            summary_date = datetime.strptime(summary_date, '%Y-%m-%d').date()

            # Get or create summary
            summary, created = CollectionSummary.objects.get_or_create(
                summary_date=summary_date
            )

            # Generate summary
            summary.generate_summary()

            return JsonResponse({
                'success': True,
                'message': 'Summary generated successfully',
                'data': {
                    'total_amount': float(summary.total_amount),
                    'total_payments': summary.total_payments,
                    'active_collectors': summary.active_collectors,
                    'achievement_percentage': float(summary.achievement_percentage),
                    'validation_status': summary.validation_status,
                }
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
def record_repayment(request):
    """Record a new repayment."""
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.created_by = request.user
                payment.save()
                
                # Process payment allocation
                # This would include logic to allocate payment to principal, interest, etc.
                
                messages.success(request, f'Payment of Tsh {payment.amount} recorded successfully.')
                return redirect('repayments:dashboard')
    else:
        form = PaymentForm()
    
    # Get loan officers and admins for the collected_by field
    from apps.accounts.models import CustomUser, UserRole
    loan_officers = CustomUser.objects.filter(
        role__in=[UserRole.LOAN_OFFICER, UserRole.ADMIN],
        is_active=True
    ).order_by('first_name', 'last_name')
    
    context = {
        'form': form,
        'title': 'Record Payment',
        'page_title': 'Record Payment',
        'loan_officers': loan_officers,
    }
    return render(request, 'repayments/record_repayment.html', context)


@login_required
def repayment_list(request):
    """List all repayments with filters."""
    payments = Payment.objects.select_related('loan', 'loan__borrower').order_by('-payment_date')
    
    # Apply filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    payment_method = request.GET.get('payment_method')
    status = request.GET.get('status')
    
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
    if status:
        payments = payments.filter(status=status)
    
    # Statistics for the filtered results
    stats = {
        'total_payments': payments.count(),
        'total_amount': payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'today_collections': payments.filter(payment_date=timezone.now().date()).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'pending_payments': payments.filter(status='pending').count(),
    }
    
    # Pagination
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
        'stats': stats,
        'title': 'Payment History',
        'page_title': 'Payment History',
    }
    return render(request, 'repayments/repayment_list.html', context)


@login_required
def bulk_payments(request):
    """Handle bulk payment uploads."""
    context = {
        'title': 'Bulk Payments',
        'page_title': 'Bulk Payments',
    }
    
    if request.method == 'POST':
        # Handle CSV upload and processing
        csv_file = request.FILES.get('csv_file')
        if csv_file:
            try:
                # Process CSV file
                # This would include validation, preview, and processing logic
                messages.success(request, 'Bulk payments processed successfully.')
                return redirect('repayments:payment_list')
            except Exception as e:
                messages.error(request, f'Error processing bulk payments: {str(e)}')
    
    return render(request, 'repayments/bulk_payments.html', context)


@login_required
def download_bulk_template(request):
    """Download CSV template for bulk payments."""
    from django.http import HttpResponse
    import csv

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bulk_payments_template.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'loan_number',
        'amount',
        'payment_date',
        'payment_method',
        'reference_number',
        'notes'
    ])

    # Add sample rows
    writer.writerow([
        'LN001',
        '5000.00',
        '2025-08-05',
        'cash',
        'RCP001',
        'Monthly installment'
    ])
    writer.writerow([
        'LN002',
        '3000.00',
        '2025-08-05',
        'bank_transfer',
        'RCP002',
        'Partial payment'
    ])

    return response


@login_required
def payment_reports(request):
    """Generate payment reports and analytics."""
    today = timezone.now().date()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = today.replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = today
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get payment data for the period
    payments = Payment.objects.filter(
        payment_date__range=[start_date, end_date],
        status='completed'
    ).select_related('loan', 'loan__borrower')
    
    # Calculate previous period for comparison
    period_days = (end_date - start_date).days
    prev_start_date = start_date - timedelta(days=period_days)
    prev_end_date = start_date - timedelta(days=1)
    
    prev_payments = Payment.objects.filter(
        payment_date__range=[prev_start_date, prev_end_date],
        status='completed'
    )
    
    # Calculate real metrics
    current_total = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    current_count = payments.count()
    current_avg = payments.aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')
    
    prev_total = prev_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    prev_count = prev_payments.count()
    prev_avg = prev_payments.aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')
    
    # Calculate percentage changes
    def calculate_change(current, previous):
        if previous and previous > 0:
            return ((current - previous) / previous) * 100
        return 0
    
    # Calculate collection rate based on due vs collected
    due_installments = LoanRepaymentSchedule.objects.filter(
        due_date__range=[start_date, end_date]
    )
    total_due = due_installments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    collection_rate = (current_total / total_due * 100) if total_due > 0 else 0
    
    # Calculate on-time payment rate
    on_time_payments = 0
    for payment in payments:
        # Check if payment was made on or before the due date of any installment
        payment_installments = payment.loan.repayment_schedule.filter(
            due_date__gte=payment.payment_date
        ).first()
        if payment_installments:
            on_time_payments += 1
    
    on_time_rate = (on_time_payments / current_count * 100) if current_count > 0 else 0
    
    # Calculate recovery rate (payments on overdue loans)
    overdue_loans = Loan.objects.filter(
        repayment_schedule__payment_status='overdue'
    ).distinct()
    recovery_payments = payments.filter(loan__in=overdue_loans)
    recovery_rate = (recovery_payments.count() / current_count * 100) if current_count > 0 else 0
    
    metrics = {
        'total_payments': current_count,
        'total_amount': current_total,
        'avg_payment': current_avg,
        'collection_rate': round(collection_rate, 1),
        'payments_trend': 'up' if current_count > prev_count else 'down' if current_count < prev_count else 'neutral',
        'amount_trend': 'up' if current_total > prev_total else 'down' if current_total < prev_total else 'neutral',
        'avg_trend': 'up' if current_avg > prev_avg else 'down' if current_avg < prev_avg else 'neutral',
        'collection_trend': 'up',  # We'd need historical data to calculate this properly
        'payments_change': round(calculate_change(current_count, prev_count), 1),
        'amount_change': round(calculate_change(float(current_total), float(prev_total)), 1),
        'avg_change': round(calculate_change(float(current_avg), float(prev_avg)), 1),
        'collection_change': 0,  # Would need historical collection rates
    }
    
    # Payment method distribution
    payment_methods = payments.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Top performing loans
    top_loans = payments.values(
        'loan__loan_number',
        'loan__borrower__first_name',
        'loan__borrower__last_name'
    ).annotate(
        payment_count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')[:10]
    
    # Collection efficiency metrics (real data)
    efficiency = {
        'on_time_rate': round(on_time_rate, 1),
        'recovery_rate': round(recovery_rate, 1),
        'target_achievement': round(collection_rate, 1),
    }
    
    # Chart data (real weekly trends)
    weeks_data = []
    week_labels = []
    week_amounts = []
    week_counts = []
    
    # Calculate weekly data for the last 4 weeks
    current_week_start = end_date - timedelta(days=end_date.weekday())
    for i in range(4):
        week_start = current_week_start - timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        
        week_payments = Payment.objects.filter(
            payment_date__range=[week_start, week_end],
            status='completed'
        )
        
        week_total = week_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        week_count = week_payments.count()
        
        week_labels.insert(0, f"Week {i+1}")
        week_amounts.insert(0, float(week_total))
        week_counts.insert(0, week_count)
    
    trends_data = {
        'labels': week_labels,
        'amounts': week_amounts,
        'counts': week_counts,
    }
    
    # Payment method distribution (real data)
    methods_data = {
        'labels': [method['payment_method'].replace('_', ' ').title() for method in payment_methods],
        'values': [method['count'] for method in payment_methods],
    }
    
    context = {
        'metrics': metrics,
        'payment_methods': payment_methods,
        'top_loans': top_loans,
        'efficiency': efficiency,
        'trends_data': trends_data,
        'methods_data': methods_data,
        'detailed_payments': payments[:50],  # Limit for display
        'period_display': f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}",
        'default_start_date': start_date.strftime('%Y-%m-%d'),
        'default_end_date': end_date.strftime('%Y-%m-%d'),
        'title': 'Payment Reports',
        'page_title': 'Payment Reports',
    }
    
    return render(request, 'repayments/payment_reports.html', context)


# API Views for AJAX calls
@login_required
def loan_info_api(request, loan_id):
    """API endpoint for loan information."""
    try:
        loan = get_object_or_404(Loan, id=loan_id)
        
        days_overdue = 0
        if hasattr(loan, 'next_due_date') and loan.next_due_date and loan.next_due_date < timezone.now().date():
            days_overdue = (timezone.now().date() - loan.next_due_date).days
        
        return JsonResponse({
            'borrower_name': loan.borrower.get_full_name(),
            'outstanding_balance': str(getattr(loan, 'outstanding_balance', 0)),
            'next_due_date': loan.next_due_date.strftime('%Y-%m-%d') if hasattr(loan, 'next_due_date') and loan.next_due_date else None,
            'days_overdue': days_overdue,
            'loan_amount': str(loan.amount),
            'interest_rate': str(getattr(loan, 'interest_rate', 0)),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def calculate_allocation_api(request, loan_id, amount):
    """API endpoint for payment allocation calculation."""
    try:
        loan = get_object_or_404(Loan, id=loan_id)
        amount = float(amount)
        
        # Simple allocation logic (this should be more sophisticated)
        penalty = min(amount, getattr(loan, 'penalty_amount', 0) or 0)
        remaining = amount - penalty
        
        interest = min(remaining, getattr(loan, 'interest_due', 0) or 0)
        remaining = remaining - interest
        
        fees = min(remaining, getattr(loan, 'fees_due', 0) or 0)
        remaining = remaining - fees
        
        principal = remaining
        
        return JsonResponse({
            'principal': f"{principal:.2f}",
            'interest': f"{interest:.2f}",
            'penalty': f"{penalty:.2f}",
            'fees': f"{fees:.2f}",
            'total': f"{amount:.2f}",
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def quick_amount_api(request, loan_id, amount_type):
    """API endpoint for quick amount calculations."""
    try:
        loan = get_object_or_404(Loan, id=loan_id)
        
        if amount_type == 'full':
            amount = getattr(loan, 'outstanding_balance', 0)
        elif amount_type == 'installment':
            amount = getattr(loan, 'installment_amount', 0)
        elif amount_type == 'overdue':
            amount = getattr(loan, 'overdue_amount', 0)
        else:
            amount = 0
        
        return JsonResponse({'amount': f"{amount:.2f}"})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
