from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import F, Q, Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import json

# Django Tables2 and Filters
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin
# from django_filters.views import FilterView  # Will be enabled after package installation
from django.views.generic.list import ListView


# Models
from .models import (
    Loan, GroupLoan, GroupLoanMember, LoanDisbursement, LoanType,
    RepaymentSchedule, Repayment, Penalty, MissedPayment, 
    WrittenOffLoan, OldLoan, PenaltyStatusChoices, RepaymentStatusChoices
)
from apps.borrowers.models import Borrower, BorrowerGroup
from apps.accounts.models import CustomUser
from apps.core.models import LoanStatusChoices, FrequencyChoices

# Forms
from . import forms
from .forms import (
    LoanForm, GroupLoanForm, ComprehensiveLoanForm, ComprehensiveGroupLoanForm,
    RepaymentForm, LoanApprovalForm, PenaltyForm
)

# Tables and Filters
from .tables import RepaidLoansTable, ExpectedRepaymentsTable, DisbursedLoansTable
# from .filters import LoanFilter, LoanBaseFilter, RepaymentScheduleFilter  # Will be enabled after package installation

# Export utilities
from apps.core.utils.export_utils import export_to_pdf, export_to_excel
from apps.core.utils.analytics_utils import (
    LoanAnalytics, prepare_data_for_export, format_currency
)

# Forms
from .forms import (
    LoanForm, GroupLoanForm, RepaymentForm, GroupRepaymentForm,
    LoanApprovalForm, LoanDisbursementForm, PenaltyForm, WrittenOffLoanForm,
    OldLoanImportForm, InterestCalculatorForm, RolloverForm, ComprehensiveLoanForm,
    ComprehensiveGroupLoanForm
)

# =============================================================================
# CLASS-BASED VIEWS FOR TABLES AND FILTERING
# =============================================================================

class DisbursedLoanListView(LoginRequiredMixin, SingleTableMixin, ListView):
    """View for listing disbursed loans with filtering and pagination."""
    model = Loan
    table_class = DisbursedLoansTable
    template_name = "loans/disbursed_loans.html"
    # filterset_class = LoanBaseFilter  # Will be enabled after package installation
    paginate_by = 25

    def get_queryset(self):
        return Loan.objects.filter(
            status=LoanStatusChoices.DISBURSED
        ).select_related("borrower", "disbursed_by", "loan_type")


class ExpectedRepaymentsView(LoginRequiredMixin, SingleTableMixin, ListView):
    """View for listing expected repayments with filtering."""
    model = RepaymentSchedule
    table_class = ExpectedRepaymentsTable
    template_name = "loans/expected_repayments.html"
    # filterset_class = RepaymentScheduleFilter  # Will be enabled after package installation
    paginate_by = 25

    def get_queryset(self):
        return RepaymentSchedule.objects.select_related(
            "loan__borrower", "loan__disbursed_by"
        ).filter(status__in=[
            RepaymentStatusChoices.PENDING, 
            RepaymentStatusChoices.MISSED
        ])


class RepaidLoansView(LoginRequiredMixin, SingleTableMixin, ListView):  # Added ListView
    """View for listing fully repaid loans with filters."""
    model = Loan
    table_class = RepaidLoansTable
    template_name = 'loans/repaid_loans.html'
    # filterset_class = LoanFilter  # Will be enabled after package installation
    paginate_by = 25

    def get_queryset(self):
        return Loan.objects.filter(
            status=LoanStatusChoices.COMPLETED
        ).select_related('borrower', 'created_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Fully Repaid Loans'
        return context


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_repayment_schedule(loan):
    """Generate repayment schedule for a disbursed loan."""
    if loan.repayment_frequency == FrequencyChoices.MONTHLY:
        frequency_months = 1
    elif loan.repayment_frequency == FrequencyChoices.WEEKLY:
        frequency_months = 0.25
    elif loan.repayment_frequency == FrequencyChoices.BIWEEKLY:
        frequency_months = 0.5
    else:
        frequency_months = 1  # Default to monthly
    
    installment_amount = loan.total_amount / loan.duration_months
    current_date = loan.disbursement_date
    
    for i in range(loan.duration_months):
        due_date = current_date + relativedelta(months=i+1)
        RepaymentSchedule.objects.create(
            loan=loan,
            due_date=due_date,
            amount_due=installment_amount,
            installment_number=i+1,
            is_group=hasattr(loan, 'group_loan')
        )


# =============================================================================
# LOAN MANAGEMENT VIEWS
# =============================================================================


@login_required
def nearing_last_installments(request):
    nearing = RepaymentSchedule.objects.filter(installment_number__gte=F('loan__duration_months') - 1)
    return render(request, 'loans/nearing_last.html', {'schedules': nearing})

@login_required
def loan_repayments(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    repayments = Repayment.objects.filter(schedule__loan=loan)
    return render(request, 'loans/loan_repayments.html', {'loan': loan, 'repayments': repayments})

@login_required
def interest_summary(request):
    loans = Loan.objects.exclude(total_interest=0)
    return render(request, 'loans/interest_summary.html', {'loans': loans})

@login_required
def receivables_view(request):
    loans = Loan.objects.filter(outstanding_balance__gt=0)
    return render(request, 'loans/interest_receivables.html', {'loans': loans})

@login_required
def add_new_loan(request):
    """Add a new individual loan using comprehensive form validation."""
    if request.method == 'POST':
        form = ComprehensiveLoanForm(request.POST, request.FILES)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.created_by = request.user
            # Set amount_approved to amount_requested by default
            if not loan.amount_approved:
                loan.amount_approved = loan.amount_requested
            loan.save()
            messages.success(request, f'Loan {loan.loan_number} created successfully!')
            return redirect('loans:disbursed_loans')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComprehensiveLoanForm()

    context = {
        'form': form,
        'title': 'Add New Individual Loan',
        'page_title': 'Register New Loan',
        'borrowers': Borrower.objects.filter(status='active').order_by('first_name', 'last_name'),
        'loan_types': LoanType.objects.filter(is_active=True).order_by('name'),
        'frequency_choices': FrequencyChoices.choices,
        'today': timezone.now().date(),
    }

    return render(request, 'loans/add_loan_backup.html', context)


@login_required
def add_group_loan(request):
    """Add a new group loan using comprehensive form validation."""
    if request.method == 'POST':
        loan_form = ComprehensiveGroupLoanForm(request.POST, request.FILES)
        
        if loan_form.is_valid():
            # Create the loan first
            loan = loan_form.save(commit=False)
            loan.created_by = request.user
            # Set amount_approved to amount_requested by default
            if not loan.amount_approved:
                loan.amount_approved = loan.amount_requested
            loan.save()
            
            # Create group loan relationship
            group_loan = GroupLoan.objects.create(
                loan=loan,
                group=loan_form.cleaned_data['group']
            )
            
            # Add all group members
            for member in loan_form.cleaned_data['group'].members.all():
                GroupLoanMember.objects.create(
                    group_loan=group_loan,
                    borrower=member,
                    responsibility_share=Decimal('100.00') / loan_form.cleaned_data['group'].members.count()
                )
            
            messages.success(request, f'Group loan {loan.loan_number} created successfully!')
            return redirect('loans:disbursed_loans')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        loan_form = ComprehensiveGroupLoanForm()

    context = {
        'form': loan_form,
        'title': 'Add New Group Loan',
        'page_title': 'Register New Group Loan',
        'groups': BorrowerGroup.objects.filter(status='active').order_by('group_name'),
        'loan_types': LoanType.objects.filter(is_active=True).order_by('name'),
        'frequency_choices': FrequencyChoices.choices,
        'today': timezone.now().date(),
    }

    return render(request, 'loans/add_group_loan_backup.html', context)


@login_required
def loan_approval(request, loan_id):
    """Approve a pending loan."""
    loan = get_object_or_404(Loan, pk=loan_id, status=LoanStatusChoices.PENDING)
    
    if request.method == 'POST':
        form = LoanApprovalForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.status = LoanStatusChoices.APPROVED
            loan.approved_by = request.user
            loan.approval_date = timezone.now().date()
            loan.save()

            # Send SMS notification
            try:
                from apps.core.sms_service import sms_service
                sms_result = sms_service.send_loan_approval(loan)
                if sms_result.get('success'):
                    messages.success(request, f'Loan {loan.loan_number} approved successfully! SMS notification sent.')
                else:
                    messages.success(request, f'Loan {loan.loan_number} approved successfully!')
                    messages.warning(request, f'SMS notification failed: {sms_result.get("error", "Unknown error")}')
            except Exception as e:
                messages.success(request, f'Loan {loan.loan_number} approved successfully!')
                messages.warning(request, f'SMS notification failed: {str(e)}')

            return redirect('loans:disbursed_loans')
    else:
        form = LoanApprovalForm(instance=loan)

    return render(request, 'loans/loan_approval.html', {
        'form': form,
        'loan': loan,
        'title': f'Approve Loan {loan.loan_number}'
    })


@login_required
def loan_disbursement(request, loan_id):
    """Disburse an approved loan."""
    loan = get_object_or_404(Loan, pk=loan_id, status=LoanStatusChoices.APPROVED)
    
    if request.method == 'POST':
        form = LoanDisbursementForm(request.POST, loan=loan)
        if form.is_valid():
            disbursement = form.save(commit=False)
            disbursement.loan = loan
            disbursement.disbursed_by = request.user
            disbursement.save()
            
            # Update loan status and generate repayment schedule
            loan.status = LoanStatusChoices.DISBURSED
            loan.disbursement_date = disbursement.disbursement_date
            loan.disbursed_by = request.user
            loan.save()
            
            # Generate repayment schedule
            _generate_repayment_schedule(loan)

            # Send SMS notification
            try:
                from apps.core.sms_service import sms_service
                sms_result = sms_service.send_loan_disbursement(loan)
                if sms_result.get('success'):
                    messages.success(request, f'Loan {loan.loan_number} disbursed successfully! SMS notification sent.')
                else:
                    messages.success(request, f'Loan {loan.loan_number} disbursed successfully!')
                    messages.warning(request, f'SMS notification failed: {sms_result.get("error", "Unknown error")}')
            except Exception as e:
                messages.success(request, f'Loan {loan.loan_number} disbursed successfully!')
                messages.warning(request, f'SMS notification failed: {str(e)}')

            return redirect('loans:disbursed_loans')
    else:
        form = LoanDisbursementForm(loan=loan)

    return render(request, 'loans/loan_disbursement.html', {
        'form': form,
        'loan': loan,
        'title': f'Disburse Loan {loan.loan_number}'
    })


# =============================================================================
# REPAYMENT MANAGEMENT VIEWS
# =============================================================================

@login_required
def record_repayment(request, schedule_id):
    """Record an individual repayment using form validation."""
    schedule = get_object_or_404(RepaymentSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = RepaymentForm(request.POST, schedule=schedule)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.schedule = schedule
            repayment.received_by = request.user
            repayment.save()
            
            # Update schedule status
            schedule.status = RepaymentStatusChoices.PAID
            schedule.save()
            
            # Update loan outstanding balance
            loan = schedule.loan
            loan.outstanding_balance -= repayment.amount_paid
            if loan.outstanding_balance <= 0:
                loan.outstanding_balance = 0
                loan.status = LoanStatusChoices.COMPLETED
            loan.save()
            
            messages.success(request, 'Repayment recorded successfully!')
            return redirect('loans:disbursed_loans')
    else:
        form = RepaymentForm(schedule=schedule)

    return render(request, 'loans/record_repayment.html', {
        'form': form,
        'schedule': schedule,
        'title': f'Record Repayment - {schedule.loan.loan_number}'
    })


@login_required
def record_group_repayment(request, schedule_id):
    """Record a group repayment using form validation."""
    schedule = get_object_or_404(RepaymentSchedule, id=schedule_id, is_group=True)
    group = schedule.loan.group_loan.group
    
    if request.method == 'POST':
        form = GroupRepaymentForm(request.POST, group=group)
        if form.is_valid():
            repayment = Repayment.objects.create(
                schedule=schedule,
                amount_paid=form.cleaned_data['amount_paid'],
                payment_date=form.cleaned_data['payment_date'],
                paid_by=form.cleaned_data['paid_by'],
                received_by=request.user,
                status=RepaymentStatusChoices.PAID
            )
            
            # Update schedule status
            schedule.status = RepaymentStatusChoices.PAID
            schedule.save()
            
            # Update loan outstanding balance
            loan = schedule.loan
            loan.outstanding_balance -= repayment.amount_paid
            if loan.outstanding_balance <= 0:
                loan.outstanding_balance = 0
                loan.status = LoanStatusChoices.COMPLETED
            loan.save()
            
            messages.success(request, 'Group repayment recorded successfully!')
            return redirect('loans:disbursed_loans')
    else:
        form = GroupRepaymentForm(group=group)

    return render(request, 'loans/record_group_repayment.html', {
        'form': form,
        'schedule': schedule,
        'group': group,
        'title': f'Record Group Repayment - {schedule.loan.loan_number}'
    })


@login_required
def rollover_repayment(request, schedule_id):
    """Roll over a repayment to a new due date."""
    schedule = get_object_or_404(RepaymentSchedule, id=schedule_id)

    if request.method == 'POST':
        form = RolloverForm(request.POST)
        if form.is_valid():
            # Mark original as rolled over
            schedule.status = RepaymentStatusChoices.ROLLED_OVER
            schedule.save()

            # Create new schedule
            RepaymentSchedule.objects.create(
                loan=schedule.loan,
                due_date=form.cleaned_data['new_due_date'],
                amount_due=schedule.amount_due + form.cleaned_data['rollover_fee'],
                status=RepaymentStatusChoices.PENDING,
                installment_number=schedule.installment_number,
                is_group=schedule.is_group
            )

            messages.success(request, 'Repayment rolled over successfully!')
            return redirect('loans:expected_repayments')
    else:
        form = RolloverForm()

    return render(request, 'loans/rollover_repayment.html', {
        'form': form,
        'schedule': schedule,
        'title': f'Roll Over Repayment - {schedule.loan.loan_number}'
    })


# =============================================================================
# REPORTING AND ANALYTICS VIEWS
# =============================================================================
# =============================================================================
# PLACEHOLDER VIEWS FOR LOAN MANAGEMENT FEATURES 
# =============================================================================

@login_required
def missed_repayments_interest(request):
    """View missed repayments and their associated penalties."""
    schedules = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.MISSED
    ).select_related('loan__borrower')
    
    penalties = Penalty.objects.filter(
        schedule__in=schedules,
        status=PenaltyStatusChoices.APPLIED
    ).select_related('loan__borrower', 'schedule')

    return render(request, 'loans/missed_repayments_interest.html', {
        'schedules': schedules,
        'penalties': penalties,
        'title': 'Missed Repayments & Interest'
    })


@login_required
def missed_schedules(request):
    """View all missed repayment schedules."""
    missed = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.MISSED
    ).select_related('loan__borrower').order_by('due_date', 'loan__loan_number')

    return render(request, 'loans/missed_schedules.html', {
        'missed': missed,
        'title': 'Missed Payment Schedules'
    })


@login_required
def loans_arrears(request):
    """View loans in arrears (with missed or defaulted payments)."""
    loans = Loan.objects.filter(
        repayment_schedules__status__in=[
            RepaymentStatusChoices.MISSED, 
            RepaymentStatusChoices.DEFAULTED
        ]
    ).distinct().select_related('borrower')
    
    return render(request, 'loans/loans_arrears.html', {
        'loans': loans,
        'title': 'Loans in Arrears'
    })


@login_required
def loans_ageing(request):
    """View loan ageing analysis."""
    today = timezone.now().date()
    ageing_loans = Loan.objects.filter(
        status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
    ).select_related('borrower')
    
    # Calculate days overdue for each loan
    for loan in ageing_loans:
        if loan.maturity_date and loan.maturity_date < today:
            loan.days_overdue = (today - loan.maturity_date).days
        else:
            loan.days_overdue = 0
    
    return render(request, 'loans/loans_ageing.html', {
        'loans': ageing_loans,
        'title': 'Loan Ageing Analysis'
    })


@login_required
def outstanding_loans(request):
    """View all loans with outstanding balances."""
    from .filters import OutstandingLoansFilter
    
    loans_queryset = Loan.objects.filter(
        outstanding_balance__gt=0
    ).select_related('borrower', 'loan_type')
    
    # Apply filters
    filter_instance = OutstandingLoansFilter(request.GET, queryset=loans_queryset)
    filtered_loans = filter_instance.qs
    
    # Calculate statistics
    total_outstanding = filtered_loans.aggregate(
        Sum('outstanding_balance')
    )['outstanding_balance__sum'] or 0
    
    total_count = filtered_loans.count()
    
    # Risk distribution (simplified calculation)
    current_loans = filtered_loans.filter(
        repayment_schedules__due_date__gte=date.today(),
        repayment_schedules__status='pending'
    ).distinct().count()
    
    overdue_1_30 = filtered_loans.filter(
        repayment_schedules__due_date__range=[
            date.today() - timedelta(days=30),
            date.today() - timedelta(days=1)
        ],
        repayment_schedules__status='pending'
    ).distinct().count()
    
    overdue_31_90 = filtered_loans.filter(
        repayment_schedules__due_date__range=[
            date.today() - timedelta(days=90),
            date.today() - timedelta(days=31)
        ],
        repayment_schedules__status='pending'
    ).distinct().count()
    
    overdue_90_plus = filtered_loans.filter(
        repayment_schedules__due_date__lt=date.today() - timedelta(days=90),
        repayment_schedules__status='pending'
    ).distinct().count()
    
    context = {
        'loans': filtered_loans,
        'filter': filter_instance,
        'total_outstanding': total_outstanding,
        'total_count': total_count,
        'current_loans': current_loans,
        'overdue_1_30': overdue_1_30,
        'overdue_31_90': overdue_31_90,
        'overdue_90_plus': overdue_90_plus,
        'title': 'Outstanding Loans'
    }
    
    return render(request, 'loans/outstanding_loans.html', context)


@login_required
def defaulted_loans(request):
    """View loans that have defaulted with statistics."""
    loans = Loan.objects.filter(
        status=LoanStatusChoices.DEFAULTED
    ).select_related('borrower', 'loan_type')

    # Calculate statistics
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    total_defaulted = loans.count()
    total_defaulted_amount = loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 0

    # This month's new defaults
    this_month = timezone.now().replace(day=1)
    new_defaults_this_month = loans.filter(
        # Using disbursement_date as proxy for when loan might have defaulted
        disbursement_date__gte=this_month
    ).count()

    # Critical defaults (over 365 days overdue)
    critical_defaults = 0  # You'll need to calculate this based on due dates

    context = {
        'loans': loans,
        'total_defaulted': total_defaulted,
        'total_defaulted_amount': total_defaulted_amount,
        'new_defaults_this_month': new_defaults_this_month,
        'critical_defaults': critical_defaults,
        'default_trend': 0,  # Calculate trend vs last month
        'recovery_rate': 0,  # Calculate recovery rate
        'recovered_this_month': 0,  # Calculate recovered this month
        'legal_actions': 0,  # Count loans in legal action
        'pending_legal': 0,  # Count pending legal actions
        'title': 'Defaulted Loans'
    }

    return render(request, 'loans/defaulted_loans.html', context)


@login_required
def written_off_loans(request):
    """View loans that have been written off."""
    written_off = WrittenOffLoan.objects.select_related(
        'loan__borrower', 'written_off_by'
    )
    
    return render(request, 'loans/written_off_loans.html', {
        'written_off_loans': written_off,
        'title': 'Written Off Loans'
    })


@login_required
def redisbursed_loans(request):
    """View loans that have been redisbursed."""
    disbursements = LoanDisbursement.objects.filter(
        is_redisbursed=True
    ).select_related('loan__borrower')
    
    return render(request, 'loans/redisbursed_loans.html', {
        'disbursements': disbursements,
        'title': 'Redisbursed Loans'
    })


@login_required
def fully_paid_loans(request):
    """View all fully paid loans with table and statistics."""
    loans = Loan.objects.filter(
        status=LoanStatusChoices.COMPLETED
    ).select_related('borrower', 'loan_type', 'created_by')

    # Create data table
    table = RepaidLoansTable(loans)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    # Calculate statistics
    from django.db.models import Sum, Avg, Count
    from django.utils import timezone

    stats = {
        'total_loans': loans.count(),
        'total_amount': loans.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0,
        'avg_duration': loans.aggregate(Avg('duration_months'))['duration_months__avg'] or 0,
        'this_month': loans.filter(
            disbursement_date__month=timezone.now().month,
            disbursement_date__year=timezone.now().year
        ).count(),
        'success_rate': 100.0  # All loans in this view are completed
    }

    context = {
        'table': table,
        'stats': stats,
        'title': 'Fully Paid Loans'
    }

    return render(request, 'loans/fully_paid_loans.html', context)


# =============================================================================
# PENALTY MANAGEMENT VIEWS
# =============================================================================


@login_required
def apply_penalty(request, schedule_id):
    """Apply penalty to a missed repayment schedule."""
    schedule = get_object_or_404(RepaymentSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = PenaltyForm(request.POST)
        if form.is_valid():
            penalty = form.save(commit=False)
            penalty.loan = schedule.loan
            penalty.schedule = schedule
            penalty.save()
            
            messages.success(request, f'Penalty of {penalty.amount} applied successfully!')
            return redirect('loans:applied_penalties')
    else:
        form = PenaltyForm()

    return render(request, 'loans/apply_penalty.html', {
        'form': form,
        'schedule': schedule,
        'title': f'Apply Penalty - {schedule.loan.loan_number}'
    })


@login_required
def applied_penalties(request):
    """View all applied penalties."""
    penalties = Penalty.objects.filter(
        status=PenaltyStatusChoices.APPLIED
    ).select_related('loan__borrower', 'schedule')
    
    return render(request, 'loans/applied_penalties.html', {
        'penalties': penalties,
        'title': 'Applied Penalties'
    })





@login_required
def clear_penalties(request):
    """Clear all applied penalties."""
    penalties = Penalty.objects.filter(status=PenaltyStatusChoices.APPLIED)
    for penalty in penalties:
        penalty.status = PenaltyStatusChoices.CLEARED
        penalty.cleared_date = timezone.now().date()
        penalty.save()
    messages.success(request, 'All penalties cleared successfully!')
    return redirect('applied_penalties')


@login_required
def write_off_loan(request, loan_id):
    """Write off a loan."""
    loan = get_object_or_404(Loan, pk=loan_id)
    
    if request.method == 'POST':
        form = WrittenOffLoanForm(request.POST)
        if form.is_valid():
            written_off = form.save(commit=False)
            written_off.loan = loan
            written_off.written_off_by = request.user
            written_off.save()
            
            # Update loan status
            loan.status = LoanStatusChoices.WRITTEN_OFF
            loan.save()
            
            messages.success(request, f'Loan {loan.loan_number} written off successfully!')
            return redirect('loans:written_off_loans')
    else:
        form = WrittenOffLoanForm()

    return render(request, 'loans/write_off_loan.html', {
        'form': form,
        'loan': loan,
        'title': f'Write Off Loan {loan.loan_number}'
    })


# =============================================================================
# PORTFOLIO AND ANALYTICS VIEWS
# =============================================================================

@login_required
def portfolio_at_risk(request):
    """View portfolio at risk analysis."""
    loans = Loan.objects.filter(
        repayment_schedules__status__in=[
            RepaymentStatusChoices.MISSED,
            RepaymentStatusChoices.DEFAULTED
        ]
    ).distinct().select_related('borrower')
    
    total_portfolio = Loan.objects.filter(
        status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
    ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
    
    at_risk_amount = loans.aggregate(
        Sum('outstanding_balance')
    )['outstanding_balance__sum'] or 0
    
    risk_percentage = (at_risk_amount / total_portfolio * 100) if total_portfolio > 0 else 0
    
    return render(request, 'loans/portfolio_at_risk.html', {
        'loans': loans,
        'total_portfolio': total_portfolio,
        'at_risk_amount': at_risk_amount,
        'risk_percentage': round(risk_percentage, 2),
        'title': 'Portfolio at Risk'
    })


@login_required
def customer_portfolio(request):
    """View customer portfolio summary."""
    portfolio = Borrower.objects.annotate(
        total_loans=Count('loans'),
        total_disbursed=Sum('loans__amount_approved'),
        total_outstanding=Sum('loans__outstanding_balance'),
        active_loans=Count('loans', filter=Q(loans__status__in=[
            LoanStatusChoices.ACTIVE, 
            LoanStatusChoices.DISBURSED
        ]))
    ).filter(total_loans__gt=0)
    
    # Calculate statistics
    total_customers = portfolio.count()
    active_portfolios = portfolio.filter(active_loans__gt=0).count()
    total_portfolio_value = portfolio.aggregate(Sum('total_disbursed'))['total_disbursed__sum'] or 0
    avg_portfolio_size = total_portfolio_value / total_customers if total_customers > 0 else 0

    return render(request, 'loans/customer_portfolio.html', {
        'customers': portfolio,  # Changed from 'portfolio' to 'customers'
        'total_customers': total_customers,
        'active_portfolios': active_portfolios,
        'total_portfolio_value': total_portfolio_value,
        'avg_portfolio_size': avg_portfolio_size,
        'title': 'Customer Portfolio Summary'
    })


@login_required
def summary_by_age_and_gender(request):
    """View demographic summary of borrowers by age and gender."""
    from django.db.models import Case, When, IntegerField
    
    # Calculate age and group by gender
    today = timezone.now().date()
    
    data = Borrower.objects.annotate(
        age=Case(
            When(date_of_birth__isnull=False, 
                 then=(today.year - F('date_of_birth__year'))),
            default=0,
            output_field=IntegerField()
        )
    ).values('gender').annotate(
        total=Count('id'),
        under_25=Count('id', filter=Q(age__lt=25)),
        between_25_40=Count('id', filter=Q(age__gte=25, age__lte=40)),
        above_40=Count('id', filter=Q(age__gt=40)),
        total_loans=Count('loans'),
        total_amount=Sum('loans__amount_approved')
    )
    
    return render(request, 'loans/summary_age_gender.html', {
        'data': data,
        'title': 'Demographics Summary by Age and Gender'
    })


@login_required
def loans_graphs_summary(request):
    """Loan analytics dashboard with charts and graphs."""
    from django.db.models import Sum, Count, Avg
    from django.utils import timezone

    # Basic statistics
    total_loans = Loan.objects.count()
    total_disbursed = Loan.objects.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
    active_loans = Loan.objects.filter(status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]).count()

    # Calculate repayment rate
    completed_loans = Loan.objects.filter(status=LoanStatusChoices.COMPLETED).count()
    repayment_rate = (completed_loans / total_loans * 100) if total_loans > 0 else 0

    # Monthly disbursement data
    summary = Loan.objects.annotate(
        month=TruncMonth('disbursement_date')
    ).values('month').annotate(
        total_loans=Count('id'),
        total_amount=Sum('amount_approved')
    ).order_by('month')

    # Convert to chart data format
    disbursement_labels = []
    disbursement_data = []
    for item in summary:
        if item['month']:
            disbursement_labels.append(item['month'].strftime('%b %Y'))
            disbursement_data.append(item['total_loans'])

    # Status distribution data
    status_data = {
        'Active': Loan.objects.filter(status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]).count(),
        'Completed': Loan.objects.filter(status=LoanStatusChoices.COMPLETED).count(),
        'Defaulted': Loan.objects.filter(status=LoanStatusChoices.DEFAULTED).count(),
        'Pending': Loan.objects.filter(status=LoanStatusChoices.PENDING).count(),
    }

    chart_data = {
        'disbursement_labels': disbursement_labels[-6:],  # Last 6 months
        'disbursement_data': disbursement_data[-6:],
        'status_labels': list(status_data.keys()),
        'status_data': list(status_data.values()),
        'repayment_labels': disbursement_labels[-6:],
        'expected_repayments': [100, 120, 110, 130, 125, 140],  # Sample data
        'actual_repayments': [95, 115, 105, 125, 120, 135],     # Sample data
        'risk_labels': ['0-30 days', '31-60 days', '61-90 days', '90+ days'],
        'risk_data': [5, 3, 2, 1]  # Sample data
    }

    context = {
        'total_loans': total_loans,
        'total_disbursed': total_disbursed,
        'active_loans': active_loans,
        'repayment_rate': round(repayment_rate, 1),
        'chart_data': chart_data,
        'title': 'Loan Analytics Dashboard'
    }

    return render(request, 'loans/loans_graphs_summary.html', context)


@login_required
def import_old_loan(request):
    """Import old loan records."""
    if request.method == 'POST':
        form = OldLoanImportForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Old loan record imported successfully!')
            return redirect('old_loans_list')
    else:
        form = OldLoanImportForm()

    return render(request, 'loans/import_old_loan.html', {
        'form': form,
        'title': 'Import Old Loan Record'
    })


@login_required
def old_loans_list(request):
    """View all imported old loan records."""
    old_loans = OldLoan.objects.select_related('borrower', 'group')
    
    return render(request, 'loans/old_loans_list.html', {
        'old_loans': old_loans,
        'title': 'Old Loan Records'
    })


@login_required
def create_group_schedule(request, group_loan_id):
    """Create repayment schedule for a group loan."""
    group_loan = get_object_or_404(GroupLoan, id=group_loan_id)
    loan = group_loan.loan

    if request.method == 'POST':
        try:
            num_installments = int(request.POST.get('installments'))
            start_date = timezone.datetime.strptime(
                request.POST.get('start_date'), '%Y-%m-%d'
            ).date()
            
            installment_amount = loan.total_amount / num_installments

            for i in range(num_installments):
                due_date = start_date + relativedelta(months=i)
                RepaymentSchedule.objects.create(
                    loan=loan,
                    due_date=due_date,
                    amount_due=installment_amount,
                    status=RepaymentStatusChoices.PENDING,
                    installment_number=i+1,
                    is_group=True
                )

            messages.success(request, 'Group repayment schedule created successfully!')
            return redirect('loans:group_loans')
            
        except Exception as e:
            messages.error(request, f'Error creating schedule: {str(e)}')

    return render(request, 'loans/create_group_schedule.html', {
        'group_loan': group_loan,
        'title': f'Create Schedule for Group Loan {group_loan.loan.loan_number}'
    })


@login_required
def group_schedules(request):
    """View all group loan repayment schedules."""
    schedules = RepaymentSchedule.objects.filter(
        is_group=True
    ).select_related('loan__borrower')
    
    return render(request, 'loans/group_schedules.html', {
        'schedules': schedules,
        'title': 'Group Loan Schedules'
    })


@login_required
def test_interest_calculator(request):
    """Interest calculation testing tool."""
    result = {}
    
    if request.method == 'POST':
        form = InterestCalculatorForm(request.POST)
        if form.is_valid():
            try:
                principal = form.cleaned_data['principal']
                rate = form.cleaned_data['interest_rate'] / 100
                duration = form.cleaned_data['duration_months']
                interest_type = form.cleaned_data['interest_type']

                if interest_type == 'reducing':
                    # Reducing balance calculation
                    monthly_rate = rate / 12
                    n = duration
                    emi = principal * (monthly_rate * (1 + monthly_rate)**n) / ((1 + monthly_rate)**n - 1)
                    total_amount = emi * n
                    total_interest = total_amount - principal
                    monthly_payment = emi
                else:
                    # Flat rate calculation
                    total_interest = principal * rate * (duration / 12)
                    total_amount = principal + total_interest
                    monthly_payment = total_amount / duration

                result = {
                    'principal': principal,
                    'interest_rate': form.cleaned_data['interest_rate'],
                    'duration_months': duration,
                    'interest_type': interest_type,
                    'total_interest': round(total_interest, 2),
                    'total_amount': round(total_amount, 2),
                    'monthly_payment': round(monthly_payment, 2)
                }

            except Exception as e:
                result['error'] = str(e)
    else:
        form = InterestCalculatorForm()

    return render(request, 'loans/interest_calculator.html', {
        'form': form,
        'result': result,
        'title': 'Interest Calculator'
    })


# =============================================================================
# ADDITIONAL LOAN MANAGEMENT VIEWS
# =============================================================================

@login_required
def summary_by_portfolio(request):
    """View loan summary by portfolio."""
    # Add logic for portfolio summary
    return render(request, 'loans/summary_by_portfolio.html', {
        'title': 'Loan Summary by Portfolio'
    })


# =============================================================================
# EXPORT VIEWS
# =============================================================================

@login_required
def export_loans_pdf(request):
    """Export loans list to PDF."""
    loans = Loan.objects.select_related('borrower', 'loan_type').all()

    # Apply filters if provided (will be enabled after package installation)
    # loan_filter = LoanFilter(request.GET, queryset=loans)
    # filtered_loans = loan_filter.qs
    filtered_loans = loans

    # Prepare data for export
    headers = [
        'Loan ID', 'Borrower', 'Loan Type', 'Principal Amount',
        'Outstanding Balance', 'Status', 'Disbursement Date', 'Maturity Date'
    ]

    data = prepare_data_for_export(
        filtered_loans,
        ['loan_id', 'borrower.full_name', 'loan_type.name', 'principal_amount',
         'outstanding_balance', 'status', 'disbursement_date', 'maturity_date']
    )

    filename = f"loans_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    title = "Loans Report"

    return export_to_pdf(data, headers, filename, title)


@login_required
def export_loans_excel(request):
    """Export loans list to Excel."""
    loans = Loan.objects.select_related('borrower', 'loan_type').all()

    # Apply filters if provided (will be enabled after package installation)
    # loan_filter = LoanFilter(request.GET, queryset=loans)
    # filtered_loans = loan_filter.qs
    filtered_loans = loans

    # Prepare data for export
    headers = [
        'Loan ID', 'Borrower', 'Loan Type', 'Principal Amount',
        'Outstanding Balance', 'Status', 'Disbursement Date', 'Maturity Date',
        'Interest Rate', 'Total Interest', 'Days Overdue'
    ]

    data = prepare_data_for_export(
        filtered_loans,
        ['loan_id', 'borrower.full_name', 'loan_type.name', 'principal_amount',
         'outstanding_balance', 'status', 'disbursement_date', 'maturity_date',
         'interest_rate', 'total_interest', 'days_overdue']
    )

    filename = f"loans_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    title = "Loans Report"

    return export_to_excel(data, headers, filename, title)


@login_required
def export_portfolio_analysis_pdf(request):
    """Export portfolio analysis to PDF."""
    loans = Loan.objects.all()

    # Calculate portfolio metrics
    portfolio_metrics = LoanAnalytics.calculate_portfolio_metrics(loans)

    # Prepare data for export
    headers = ['Metric', 'Value']
    data = []

    # Basic metrics
    basic_metrics = portfolio_metrics.get('basic_metrics', {})
    data.extend([
        ['Total Loans', portfolio_metrics.get('total_loans', 0)],
        ['Total Disbursed', format_currency(basic_metrics.get('total_disbursed', 0))],
        ['Total Outstanding', format_currency(basic_metrics.get('total_outstanding', 0))],
        ['Average Loan Size', format_currency(basic_metrics.get('avg_loan_size', 0))],
        ['Total Interest Earned', format_currency(basic_metrics.get('total_interest_earned', 0))],
    ])

    # Risk metrics
    risk_metrics = portfolio_metrics.get('risk_metrics', {})
    data.extend([
        ['', ''],  # Empty row
        ['RISK METRICS', ''],
        ['Portfolio at Risk', format_currency(risk_metrics.get('portfolio_at_risk', 0))],
        ['PAR Ratio (%)', f"{risk_metrics.get('par_ratio', 0):.2f}%"],
        ['Default Rate (%)', f"{risk_metrics.get('default_rate', 0):.2f}%"],
        ['Completion Rate (%)', f"{risk_metrics.get('completion_rate', 0):.2f}%"],
    ])

    # Status breakdown
    status_breakdown = portfolio_metrics.get('status_breakdown', {})
    data.extend([
        ['', ''],  # Empty row
        ['STATUS BREAKDOWN', ''],
    ])

    for status, metrics in status_breakdown.items():
        data.extend([
            [f"{status.title()} - Count", metrics.get('count', 0)],
            [f"{status.title()} - Amount", format_currency(metrics.get('amount', 0))],
            [f"{status.title()} - Percentage", f"{metrics.get('percentage', 0):.2f}%"],
        ])

    filename = f"portfolio_analysis_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    title = "Loan Portfolio Analysis"

    return export_to_pdf(data, headers, filename, title)


@login_required
def export_overdue_loans_pdf(request):
    """Export overdue loans to PDF."""
    overdue_loans = Loan.objects.filter(status='overdue').select_related('borrower', 'loan_type')

    headers = [
        'Loan ID', 'Borrower', 'Phone', 'Principal Amount',
        'Outstanding Balance', 'Days Overdue', 'Penalty Amount', 'Last Payment Date'
    ]

    data = prepare_data_for_export(
        overdue_loans,
        ['loan_id', 'borrower.full_name', 'borrower.phone_number', 'principal_amount',
         'outstanding_balance', 'days_overdue', 'penalty_amount', 'last_payment_date']
    )

    filename = f"overdue_loans_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    title = "Overdue Loans Report"

    return export_to_pdf(data, headers, filename, title)


@login_required
def export_overdue_loans_excel(request):
    """Export overdue loans to Excel."""
    overdue_loans = Loan.objects.filter(status='overdue').select_related('borrower', 'loan_type')

    headers = [
        'Loan ID', 'Borrower', 'Phone', 'Email', 'Principal Amount',
        'Outstanding Balance', 'Days Overdue', 'Penalty Amount', 'Last Payment Date',
        'Next Payment Due', 'Loan Officer', 'District', 'Region'
    ]

    data = prepare_data_for_export(
        overdue_loans,
        ['loan_id', 'borrower.full_name', 'borrower.phone_number', 'borrower.email',
         'principal_amount', 'outstanding_balance', 'days_overdue', 'penalty_amount',
         'last_payment_date', 'next_payment_due', 'loan_officer',
         'borrower.district', 'borrower.region']
    )

    filename = f"overdue_loans_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    title = "Overdue Loans Report"

    return export_to_excel(data, headers, filename, title)

@login_required
def record_old_loans(request):
    """Import or record old loans."""
    if request.method == 'POST':
        form = OldLoanImportForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Old loan record imported successfully!')
            return redirect('loans:record_old_loans')
    else:
        form = OldLoanImportForm()
    
    return render(request, 'loans/record_old_loans.html', {
        'form': form,
        'title': 'Import/Record Old Loans'
    })

@login_required
def rollover_repayments(request):
    """Handle rollover repayments."""
    schedules = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.PENDING
    ).select_related('loan__borrower')
    
    return render(request, 'loans/rollover_repayments.html', {
        'schedules': schedules,
        'title': 'Rollover Repayments'
    })

@login_required
def create_schedules(request):
    """Create individual loan schedules."""
    loans = Loan.objects.filter(
        status=LoanStatusChoices.APPROVED
    ).select_related('borrower')
    
    return render(request, 'loans/create_schedules.html', {
        'loans': loans,
        'title': 'Create Loan Schedules'
    })

@login_required
def create_group_schedules(request):
    """Create group loan schedules."""
    group_loans = GroupLoan.objects.filter(
        loan__status=LoanStatusChoices.APPROVED
    ).select_related('loan', 'group')
    
    return render(request, 'loans/create_group_schedules.html', {
        'group_loans': group_loans,
        'title': 'Create Group Schedules'
    })

@login_required
def penalties(request):
    """View all penalties applied to loans."""
    penalties = Penalty.objects.select_related('loan__borrower', 'schedule').filter(
        status=PenaltyStatusChoices.APPLIED
    )
    return render(request, 'loans/penalties.html', {
        'penalties': penalties,
        'title': 'Penalties'
    })

@login_required
def add_penalty_form(request):
    """Show form to add penalty (without requiring schedule_id)."""
    # Get all missed schedules that can have penalties applied
    missed_schedules = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.MISSED
    ).select_related('loan__borrower')

    return render(request, 'loans/add_penalty.html', {
        'missed_schedules': missed_schedules,
        'title': 'Add Penalty'
    })

@login_required
def missed_payments(request):
    """View all missed payments."""
    missed_schedules = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.MISSED
    ).select_related('loan__borrower').order_by('due_date', 'loan__loan_number')

    return render(request, 'loans/missed_payments.html', {
        'missed_payments': missed_schedules,
        'title': 'Missed Payments'
    })

@login_required
def loan_list(request):
    """Placeholder view for loan list."""
    loans = Loan.objects.all()
    return render(request, 'loans/loan_list.html', {'loans': loans})


@login_required
def pending_loans_list(request):
    """List all pending loans for approval officers."""
    pending_loans = Loan.objects.filter(
        status=LoanStatusChoices.PENDING
    ).select_related('borrower', 'loan_type', 'created_by').order_by('-created_at')
    
    # For group loans, we need to filter via the related loan field
    pending_group_loans = GroupLoan.objects.filter(
        loan__status=LoanStatusChoices.PENDING
    ).select_related('group', 'loan__loan_type', 'loan__created_by').order_by('-loan__created_at')
    
    context = {
        'title': 'Pending Loan Applications',
        'pending_loans': pending_loans,
        'pending_group_loans': pending_group_loans,
        'total_pending': pending_loans.count() + pending_group_loans.count(),
    }
    
    return render(request, 'loans/pending_loans.html', context)


@login_required
def export_customer_portfolio(request):
    """Export customer portfolio to CSV."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_portfolio.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Borrower ID', 'Name', 'Phone', 'Total Loans', 'Active Loans',
        'Total Amount', 'Outstanding Balance', 'Status'
    ])

    # Get borrowers with loan data
    borrowers = Borrower.objects.filter(loans__isnull=False).distinct()

    for borrower in borrowers:
        loans = borrower.loans.all()
        active_loans = loans.filter(status='active')
        total_amount = loans.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
        outstanding = loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 0

        writer.writerow([
            borrower.borrower_id,
            borrower.get_full_name(),
            borrower.phone_number,
            loans.count(),
            active_loans.count(),
            total_amount,
            outstanding,
            borrower.status
        ])

    return response


@login_required
def group_loans(request):
    """View all group loans."""
    group_loans = GroupLoan.objects.all().select_related('loan', 'group').order_by('-loan__loan_number')

    context = {
        'group_loans': group_loans,
        'title': 'Group Loans'
    }
    return render(request, 'loans/group_loans.html', context)


@login_required
def borrowers_api(request):
    """API endpoint to fetch borrowers for autocomplete."""
    from apps.borrowers.models import Borrower
    
    borrowers = Borrower.objects.all().values(
        'id', 'borrower_id', 'first_name', 'last_name', 'phone_number'
    )
    
    borrowers_list = list(borrowers)
    return JsonResponse(borrowers_list, safe=False)
