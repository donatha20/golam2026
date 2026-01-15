from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import F, Q, Count, Sum, Avg, OuterRef, Subquery
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
    WrittenOffLoan, OldLoan, PenaltyStatusChoices, RepaymentStatusChoices,
    NPLCategoryChoices, NPLStatusChoices
)
from apps.borrowers.models import Borrower, BorrowerGroup, BorrowerStatus
from apps.accounts.models import CustomUser
from apps.core.models import LoanStatusChoices, FrequencyChoices, StatusChoices

# Forms
from . import forms
from .forms import (
    LoanForm, GroupLoanForm, ComprehensiveLoanForm, ComprehensiveGroupLoanForm,
    RepaymentForm, LoanApprovalForm, PenaltyForm
)

# Tables and Filters
from .tables import RepaidLoansTable, ExpectedRepaymentsTable, DisbursedLoansTable, NonPerformingLoansTable
# from .filters import LoanFilter, LoanBaseFilter, RepaymentScheduleFilter  # Will be enabled after package installation

# Export utilities
from apps.core.utils.export_utils import export_to_pdf, export_to_excel
from apps.core.utils.analytics_utils import format_currency

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


class NonPerformingLoansView(LoginRequiredMixin, SingleTableMixin, ListView):
    """View for listing non-performing loans (NPLs) - loans with missed payments or overdue."""
    model = Loan
    table_class = NonPerformingLoansTable
    template_name = 'loans/non_performing_loans.html'
    paginate_by = 25

    def get_queryset(self):
        """
        Get non-performing loans: loans that are overdue (past maturity date) 
        or have missed repayment schedules.
        NPL classification: 90+ days overdue
        """
        # Use the manager method for non-performing loans
        queryset = Loan.objects.non_performing().select_related(
            'borrower', 'loan_type', 'disbursed_by', 'assigned_recovery_officer'
        )
        
        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(loan_number__icontains=search) |
                Q(borrower__first_name__icontains=search) |
                Q(borrower__last_name__icontains=search) |
                Q(borrower__borrower_id__icontains=search)
            )
        
        # Apply NPL category filter using manager methods
        npl_category = self.request.GET.get('npl_category')
        if npl_category:
            if npl_category == 'watch':
                queryset = Loan.objects.watch_loans()
            elif npl_category == 'substandard':
                queryset = Loan.objects.substandard_loans()
            elif npl_category == 'doubtful':
                queryset = Loan.objects.doubtful_loans()
            elif npl_category == 'loss':
                queryset = Loan.objects.loss_loans()
            
            # Re-apply search filter if category was selected
            if search:
                queryset = queryset.filter(
                    Q(loan_number__icontains=search) |
                    Q(borrower__first_name__icontains=search) |
                    Q(borrower__last_name__icontains=search) |
                    Q(borrower__borrower_id__icontains=search)
                )
            
            queryset = queryset.select_related(
                'borrower', 'loan_type', 'disbursed_by', 'assigned_recovery_officer'
            )
        
        # Apply NPL status filter
        npl_status = self.request.GET.get('npl_status')
        if npl_status:
            queryset = queryset.filter(npl_status=npl_status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use manager methods for category counts
        watch_count = Loan.objects.watch_loans().count()
        substandard_count = Loan.objects.substandard_loans().count()
        doubtful_count = Loan.objects.doubtful_loans().count()
        loss_count = Loan.objects.loss_loans().count()
        
        # Calculate NPL statistics
        npl_loans = Loan.objects.non_performing()
        total_npl_count = npl_loans.count()
        total_npl_amount = npl_loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 0
        total_provision = npl_loans.aggregate(Sum('npl_provision_amount'))['npl_provision_amount__sum'] or 0
        
        # Get all active/disbursed loans for portfolio calculation
        all_loans = Loan.objects.filter(
            status__in=[LoanStatusChoices.DISBURSED, LoanStatusChoices.ACTIVE]
        )
        total_portfolio = all_loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 1
        
        # NPL Ratio
        npl_ratio = (Decimal(str(total_npl_amount)) / Decimal(str(total_portfolio)) * 100) if total_portfolio > 0 else 0
        
        context.update({
            'title': 'Non-Performing Loans',
            'total_npl_count': total_npl_count,
            'total_npl_amount': total_npl_amount,
            'npl_ratio': round(npl_ratio, 2),
            'total_portfolio': total_portfolio,
            'total_provision': total_provision,
            'watch_count': watch_count,
            'substandard_count': substandard_count,
            'doubtful_count': doubtful_count,
            'loss_count': loss_count,
            'npl_status_choices': NPLStatusChoices.choices,
        })
        return context


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_repayment_schedule(loan):
    """Generate repayment schedule for a disbursed loan."""
    if hasattr(loan, "generate_repayment_schedule"):
        loan.generate_repayment_schedule()
        return

    installment_amount = loan.total_amount / loan.duration_months
    current_date = loan.disbursement_date

    for i in range(loan.duration_months):
        due_date = current_date + relativedelta(months=i + 1)
        RepaymentSchedule.objects.create(
            loan=loan,
            due_date=due_date,
            amount_due=installment_amount,
            installment_number=i + 1,
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
def loan_detail(request, loan_id):
    """View to display detailed information about a specific loan."""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get repayment schedule
    schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('due_date')
    
    # Get actual repayments
    repayments = Repayment.objects.filter(schedule__loan=loan).order_by('-payment_date')
    
    # Calculate loan statistics
    total_expected = schedule.aggregate(total=Sum('amount_due'))['total'] or 0
    total_paid = repayments.aggregate(total=Sum('amount_paid'))['total'] or 0
    outstanding_balance = total_expected - total_paid
    
    context = {
        'loan': loan,
        'schedule': schedule,
        'repayments': repayments,
        'total_expected': total_expected,
        'total_paid': total_paid,
        'outstanding_balance': outstanding_balance,
        'today': timezone.now().date(),
    }
    
    return render(request, 'loans/loan_detail.html', context)

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
        'borrowers': Borrower.objects.filter(status=BorrowerStatus.ACTIVE).order_by('first_name', 'last_name'),
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
        'groups': BorrowerGroup.objects.filter(status=StatusChoices.ACTIVE).order_by('group_name'),
        'loan_types': LoanType.objects.filter(is_active=True).order_by('name'),
        'frequency_choices': FrequencyChoices.choices,
        'today': timezone.now().date(),
    }

    return render(request, 'loans/add_group_loan_backup.html', context)


@login_required
def loan_approval(request, loan_id):
    """Approve and automatically disburse a pending loan."""
    loan = get_object_or_404(Loan, pk=loan_id, status=LoanStatusChoices.PENDING)
    
    if request.method == 'POST':
        form = LoanApprovalForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)
            
            # Step 1: Approve the loan
            loan.status = LoanStatusChoices.APPROVED
            loan.approved_by = request.user
            loan.approval_date = timezone.now().date()
            
            # Step 2: Automatically disburse the loan
            loan.status = LoanStatusChoices.DISBURSED
            loan.disbursed_by = request.user
            loan.disbursement_date = timezone.now().date()
            
            loan.save()
            
            # Step 3: Generate repayment schedule
            _generate_repayment_schedule(loan)
            
            # Step 4: Create disbursement record (if needed)
            try:
                from .models import LoanDisbursement
                LoanDisbursement.objects.create(
                    loan=loan,
                    disbursement_date=loan.disbursement_date,
                    amount=loan.amount_approved or loan.amount_requested,
                    disbursed_by=request.user,
                    notes=f'Auto-disbursed after approval by {request.user.get_full_name()}'
                )
            except Exception as e:
                # Continue even if disbursement record creation fails
                print(f"Warning: Could not create disbursement record: {e}")

            # Send SMS notification for approval and disbursement
            try:
                from apps.core.sms_service import sms_service
                sms_result = sms_service.send_loan_disbursement(loan)
                if sms_result.get('success'):
                    messages.success(request, f'Loan {loan.loan_number} approved and disbursed successfully! SMS notification sent.')
                else:
                    messages.success(request, f'Loan {loan.loan_number} approved and disbursed successfully!')
                    messages.warning(request, f'SMS notification failed: {sms_result.get("error", "Unknown error")}')
            except Exception as e:
                messages.success(request, f'Loan {loan.loan_number} approved and disbursed successfully!')
                messages.warning(request, f'SMS notification failed: {str(e)}')

            return redirect('loans:disbursed_loans')
    else:
        form = LoanApprovalForm(instance=loan)

    return render(request, 'loans/loan_approval.html', {
        'form': form,
        'loan': loan,
        'title': f'Approve & Disburse Loan {loan.loan_number}'
    })


@login_required
def loan_rejection(request, loan_id):
    """Reject a pending loan."""
    loan = get_object_or_404(Loan, pk=loan_id, status=LoanStatusChoices.PENDING)
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        rejection_reason = data.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            return JsonResponse({'success': False, 'error': 'Rejection reason is required'})
        
        # Update loan status and save rejection reason
        loan.status = LoanStatusChoices.REJECTED
        loan.rejection_reason = rejection_reason
        loan.rejected_by = request.user
        loan.rejection_date = timezone.now().date()
        loan.save()

        # Send SMS notification
        try:
            from apps.core.sms_service import sms_service
            sms_result = sms_service.send_loan_rejection(loan)
            if sms_result.get('success'):
                return JsonResponse({
                    'success': True, 
                    'message': f'Loan {loan.loan_number} rejected successfully! SMS notification sent.',
                    'redirect_url': '/loans/pending/'
                })
            else:
                return JsonResponse({
                    'success': True, 
                    'message': f'Loan {loan.loan_number} rejected successfully!',
                    'warning': f'SMS notification failed: {sms_result.get("error", "Unknown error")}',
                    'redirect_url': '/loans/pending/'
                })
        except Exception as e:
            return JsonResponse({
                'success': True, 
                'message': f'Loan {loan.loan_number} rejected successfully!',
                'warning': f'SMS notification failed: {str(e)}',
                'redirect_url': '/loans/pending/'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


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
            
            # Update schedule totals and status
            schedule.amount_paid = (schedule.amount_paid or Decimal('0')) + repayment.amount_paid
            schedule.save(update_fields=['amount_paid'])
            schedule.update_status()
            
            # Update loan outstanding balance
            loan = schedule.loan
            total_paid = Repayment.objects.filter(
                schedule__loan=loan
            ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
            loan.total_paid = total_paid
            loan.outstanding_balance = loan.total_amount - total_paid
            if loan.outstanding_balance <= 0 and loan.status in [
                LoanStatusChoices.ACTIVE,
                LoanStatusChoices.DISBURSED
            ]:
                loan.outstanding_balance = Decimal('0')
                loan.status = LoanStatusChoices.COMPLETED
            loan.save(update_fields=['total_paid', 'outstanding_balance', 'status'])
            
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
            
            # Update schedule totals and status
            schedule.amount_paid = (schedule.amount_paid or Decimal('0')) + repayment.amount_paid
            schedule.save(update_fields=['amount_paid'])
            schedule.update_status()
            
            # Update loan outstanding balance
            loan = schedule.loan
            total_paid = Repayment.objects.filter(
                schedule__loan=loan
            ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
            loan.total_paid = total_paid
            loan.outstanding_balance = loan.total_amount - total_paid
            if loan.outstanding_balance <= 0 and loan.status in [
                LoanStatusChoices.ACTIVE,
                LoanStatusChoices.DISBURSED
            ]:
                loan.outstanding_balance = Decimal('0')
                loan.status = LoanStatusChoices.COMPLETED
            loan.save(update_fields=['total_paid', 'outstanding_balance', 'status'])
            
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
    """
    Loans in arrears = loans with an unpaid instalment that is
    between 0 and 5 days overdue (grace period).
    """

    today = timezone.localdate()

    overdue_statuses = [
        RepaymentStatusChoices.PENDING,
        RepaymentStatusChoices.MISSED,
        RepaymentStatusChoices.DEFAULTED,
    ]

    # Oldest overdue instalment per loan
    oldest_overdue_due_date_sq = RepaymentSchedule.objects.filter(
        loan_id=OuterRef("pk"),
        due_date__lt=today,
        status__in=overdue_statuses,
    ).order_by("due_date").values("due_date")[:1]

    loans = (
        Loan.objects.filter(
            status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
        )
        .select_related("borrower")
        .annotate(oldest_overdue_due_date=Subquery(oldest_overdue_due_date_sq))
    )

    arrears_loans = []

    for loan in loans:
        if loan.oldest_overdue_due_date:
            days_overdue = (today - loan.oldest_overdue_due_date).days

            # Arrears = 0 to 5 days late
            if 0 <= days_overdue <= 5:
                loan.days_overdue = days_overdue
                arrears_loans.append(loan)

    return render(request, "loans/loans_arrears.html", {
        "loans": arrears_loans,
        "title": "Loans in Arrears (0–5 Days Past Due)",
        "as_of": today,
    })

@login_required
def loans_ageing(request):
    """
    Loan ageing analysis based on the OLDEST overdue unpaid instalment.
    This is the standard "days past due" approach used in lending.
    """

    today = timezone.localdate()

    # Define what counts as "unpaid / problematic"
    # Add/adjust statuses to match your system
    overdue_statuses = [
        RepaymentStatusChoices.PENDING,    # if you have it
        RepaymentStatusChoices.MISSED,
        RepaymentStatusChoices.DEFAULTED,
        # RepaymentStatusChoices.PARTIAL,  # optional if you have partial payments
    ]

    # Subquery: oldest overdue repayment due_date per loan
    oldest_overdue_due_date_sq = RepaymentSchedule.objects.filter(
        loan_id=OuterRef("pk"),
        due_date__lt=today,
        status__in=overdue_statuses,
    ).order_by("due_date").values("due_date")[:1]

    loans = (
        Loan.objects.filter(
            status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
        )
        .select_related("borrower")
        .annotate(oldest_overdue_due_date=Subquery(oldest_overdue_due_date_sq))
        .order_by("-id")
    )

    # Compute days_overdue + bucket in Python (fast, no extra queries)
    for loan in loans:
        if loan.oldest_overdue_due_date:
            loan.days_overdue = (today - loan.oldest_overdue_due_date).days
        else:
            loan.days_overdue = 0

        d = loan.days_overdue
        if d == 0:
            loan.ageing_bucket = "Current"
        elif 1 <= d <= 30:
            loan.ageing_bucket = "1–30"
        elif 31 <= d <= 60:
            loan.ageing_bucket = "31–60"
        elif 61 <= d <= 90:
            loan.ageing_bucket = "61–90"
        else:
            loan.ageing_bucket = "90+"

    return render(request, "loans/loans_ageing.html", {
        "loans": loans,
        "title": "Loan Ageing Analysis",
        "as_of": today,
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
        repayment_schedules__status=RepaymentStatusChoices.PENDING
    ).distinct().count()
    
    overdue_1_30 = filtered_loans.filter(
        repayment_schedules__due_date__range=[
            date.today() - timedelta(days=30),
            date.today() - timedelta(days=1)
        ],
        repayment_schedules__status=RepaymentStatusChoices.PENDING
    ).distinct().count()
    
    overdue_31_90 = filtered_loans.filter(
        repayment_schedules__due_date__range=[
            date.today() - timedelta(days=90),
            date.today() - timedelta(days=31)
        ],
        repayment_schedules__status=RepaymentStatusChoices.PENDING
    ).distinct().count()
    
    overdue_90_plus = filtered_loans.filter(
        repayment_schedules__due_date__lt=date.today() - timedelta(days=90),
        repayment_schedules__status=RepaymentStatusChoices.PENDING
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

from django.db.models import OuterRef, Subquery, Sum
from django.utils import timezone


@login_required
def portfolio_at_risk(request):
    today = timezone.localdate()

    overdue_statuses = [
        RepaymentStatusChoices.PENDING,
        RepaymentStatusChoices.MISSED,
        RepaymentStatusChoices.DEFAULTED,
    ]

    # Oldest overdue instalment per loan
    oldest_due_sq = RepaymentSchedule.objects.filter(
        loan_id=OuterRef("pk"),
        due_date__lt=today,
        status__in=overdue_statuses,
    ).order_by("due_date").values("due_date")[:1]

    loans = (
        Loan.objects.filter(
            status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
        )
        .select_related("borrower")
        .annotate(oldest_overdue_due_date=Subquery(oldest_due_sq))
    )

    par_loans = []
    at_risk_amount = 0

    for loan in loans:
        if loan.oldest_overdue_due_date:
            days = (today - loan.oldest_overdue_due_date).days

            # PAR = 6 to 30 days overdue
            if 6 <= days <= 30:
                loan.days_overdue = days
                par_loans.append(loan)
                at_risk_amount += loan.outstanding_balance

    total_portfolio = Loan.objects.filter(
        status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
    ).aggregate(Sum("amount_approved"))["amount_approved__sum"] or 0

    risk_percentage = (
        (at_risk_amount / total_portfolio) * 100
        if total_portfolio > 0 else 0
    )

    return render(request, "loans/portfolio_at_risk.html", {
        "loans": par_loans,
        "total_portfolio": total_portfolio,
        "at_risk_amount": at_risk_amount,
        "risk_percentage": round(risk_percentage, 2),
        "title": "Portfolio at Risk (6–30 Days)",
        "as_of": today,
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
    """Enhanced loan analytics dashboard with beautiful charts and graphs."""
    from django.db.models import Sum, Count, Avg
    from django.utils import timezone
    from django.db.models.functions import TruncMonth

    # Basic statistics
    total_loans = Loan.objects.count()
    total_disbursed = Loan.objects.exclude(status__in=[LoanStatusChoices.PENDING, LoanStatusChoices.REJECTED]).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
    active_loans = Loan.objects.filter(status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED, LoanStatusChoices.APPROVED]).count()

    # Calculate repayment rate
    completed_loans = Loan.objects.filter(status=LoanStatusChoices.COMPLETED).count()
    repayment_rate = (completed_loans / total_loans * 100) if total_loans > 0 else 0

    # Enhanced monthly data - Get data for all months in 2025
    current_year = timezone.now().year
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Monthly disbursement amounts - Include ALL loan statuses except pending/rejected
    disbursement_summary = Loan.objects.filter(
        disbursement_date__year=current_year
    ).exclude(
        status__in=[LoanStatusChoices.PENDING, LoanStatusChoices.REJECTED]
    ).annotate(
        month=TruncMonth('disbursement_date')
    ).values('month').annotate(
        total_amount=Sum('amount_approved'),
        total_loans=Count('id')
    ).order_by('month')

    # Monthly repayment amounts
    from apps.repayments.models import Payment
    repayment_summary = Payment.objects.filter(
        payment_date__year=current_year,
        status='completed'
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total_amount=Sum('amount')
    ).order_by('month')

    # Monthly defaulted loan amounts
    defaulted_summary = Loan.objects.filter(
        status=LoanStatusChoices.DEFAULTED,
        disbursement_date__year=current_year
    ).annotate(
        month=TruncMonth('disbursement_date')
    ).values('month').annotate(
        total_amount=Sum('amount_approved')
    ).order_by('month')

    # Prepare data arrays for all 12 months
    disbursed_amounts = [0] * 12
    repayment_amounts = [0] * 12
    defaulted_amounts = [0] * 12

    # Fill disbursement data
    for item in disbursement_summary:
        if item['month']:
            month_index = item['month'].month - 1
            disbursed_amounts[month_index] = float(item['total_amount'] or 0)

    # Fill repayment data
    for item in repayment_summary:
        if item['month']:
            month_index = item['month'].month - 1
            repayment_amounts[month_index] = float(item['total_amount'] or 0)

    # Fill defaulted loan data
    for item in defaulted_summary:
        if item['month']:
            month_index = item['month'].month - 1
            defaulted_amounts[month_index] = float(item['total_amount'] or 0)

    # Status distribution data - Count ALL loan statuses
    status_data = {
        'Approved': Loan.objects.filter(status=LoanStatusChoices.APPROVED).count(),
        'Active': Loan.objects.filter(status=LoanStatusChoices.ACTIVE).count(),
        'Disbursed': Loan.objects.filter(status=LoanStatusChoices.DISBURSED).count(),
        'Completed': Loan.objects.filter(status=LoanStatusChoices.COMPLETED).count(),
        'Defaulted': Loan.objects.filter(status=LoanStatusChoices.DEFAULTED).count(),
        'Rejected': Loan.objects.filter(status=LoanStatusChoices.REJECTED).count(),
        'Pending': Loan.objects.filter(status=LoanStatusChoices.PENDING).count(),
    }

    # Remove zero counts for cleaner display
    status_data = {k: v for k, v in status_data.items() if v > 0}

    # Portfolio at Risk calculation using RepaymentSchedule
    from django.utils import timezone
    from datetime import timedelta
    from .models import RepaymentSchedule
    
    today = timezone.now().date()
    
    # Calculate days overdue for different buckets using RepaymentSchedule
    # Only if RepaymentSchedule data exists
    try:
        risk_0_30 = RepaymentSchedule.objects.filter(
            loan__status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED],
            status=RepaymentStatusChoices.PENDING,
            due_date__lt=today,
            due_date__gte=today - timedelta(days=30)
        ).values('loan').distinct().count()
        
        risk_31_60 = RepaymentSchedule.objects.filter(
            loan__status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED],
            status=RepaymentStatusChoices.PENDING,
            due_date__lt=today - timedelta(days=30),
            due_date__gte=today - timedelta(days=60)
        ).values('loan').distinct().count()
        
        risk_61_90 = RepaymentSchedule.objects.filter(
            loan__status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED],
            status=RepaymentStatusChoices.PENDING,
            due_date__lt=today - timedelta(days=60),
            due_date__gte=today - timedelta(days=90)
        ).values('loan').distinct().count()
        
        risk_90_plus = RepaymentSchedule.objects.filter(
            loan__status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED],
            status=RepaymentStatusChoices.PENDING,
            due_date__lt=today - timedelta(days=90)
        ).values('loan').distinct().count()
    except:
        # Fallback if no repayment schedule data
        risk_0_30 = risk_31_60 = risk_61_90 = risk_90_plus = 0

    # Convert to percentages
    total_active = active_loans
    risk_percentages = [
        round((risk_0_30 / total_active * 100), 1) if total_active > 0 else 0,
        round((risk_31_60 / total_active * 100), 1) if total_active > 0 else 0,
        round((risk_61_90 / total_active * 100), 1) if total_active > 0 else 0,
        round((risk_90_plus / total_active * 100), 1) if total_active > 0 else 0,
    ]

    # Debug: Print actual data
    print(f"Debug - Disbursed amounts: {disbursed_amounts}")
    print(f"Debug - Status data: {status_data}")
    print(f"Debug - Total disbursed: {total_disbursed}")
    print(f"Debug - Total loans: {total_loans}")
    print(f"Debug - Active loans: {active_loans}")

    chart_data = {
        'disbursement_labels': months,
        'disbursed_amounts': disbursed_amounts,
        'repayment_amounts': repayment_amounts,
        'defaulted_amounts': defaulted_amounts,
        'status_labels': list(status_data.keys()),
        'status_data': list(status_data.values()),
        'risk_labels': ['0-30 days', '31-60 days', '61-90 days', '90+ days'],
        'risk_data': risk_percentages
    }

    context = {
        'total_loans': total_loans,
        'total_disbursed': total_disbursed,
        'active_loans': active_loans,
        'repayment_rate': round(repayment_rate, 1),
        'chart_data': chart_data,
        'title': 'Enhanced Loan Analytics Dashboard'
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
        'Loan Number', 'Borrower', 'Loan Type', 'Approved Amount',
        'Outstanding Balance', 'Status', 'Disbursement Date', 'Maturity Date'
    ]

    data = []
    for loan in filtered_loans:
        data.append([
            loan.loan_number,
            loan.borrower.get_full_name(),
            loan.loan_type.name if loan.loan_type else '',
            loan.amount_approved or loan.amount_requested,
            loan.outstanding_balance,
            loan.get_status_display() if hasattr(loan, 'get_status_display') else loan.status,
            loan.disbursement_date,
            loan.maturity_date,
        ])

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
        'Loan Number', 'Borrower', 'Loan Type', 'Approved Amount',
        'Outstanding Balance', 'Status', 'Disbursement Date', 'Maturity Date',
        'Interest Rate', 'Total Interest', 'Days Overdue'
    ]

    data = []
    for loan in filtered_loans:
        data.append([
            loan.loan_number,
            loan.borrower.get_full_name(),
            loan.loan_type.name if loan.loan_type else '',
            loan.amount_approved or loan.amount_requested,
            loan.outstanding_balance,
            loan.get_status_display() if hasattr(loan, 'get_status_display') else loan.status,
            loan.disbursement_date,
            loan.maturity_date,
            loan.interest_rate,
            loan.total_interest,
            loan.days_overdue,
        ])

    filename = f"loans_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    title = "Loans Report"

    return export_to_excel(data, headers, filename, title)


@login_required
def export_portfolio_analysis_pdf(request):
    """Export portfolio analysis to PDF."""
    loans = Loan.objects.all()

    # Calculate portfolio metrics
    total_loans = loans.count()
    basic_metrics = loans.aggregate(
        total_disbursed=Sum('amount_approved'),
        total_outstanding=Sum('outstanding_balance'),
        avg_loan_size=Avg('amount_approved'),
        total_interest_earned=Sum('total_interest'),
    )

    status_breakdown = {}
    status_mappings = [
        (LoanStatusChoices.ACTIVE, 'active'),
        (LoanStatusChoices.COMPLETED, 'completed'),
        (LoanStatusChoices.DEFAULTED, 'defaulted'),
        (LoanStatusChoices.WRITTEN_OFF, 'written_off'),
    ]
    for status_value, label in status_mappings:
        count = loans.filter(status=status_value).count()
        amount = loans.filter(status=status_value).aggregate(
            total=Sum('outstanding_balance')
        )['total'] or Decimal('0')
        status_breakdown[label] = {
            'count': count,
            'amount': amount,
            'percentage': (count / total_loans) * 100 if total_loans > 0 else 0,
        }

    portfolio_at_risk = Loan.objects.overdue().aggregate(
        amount=Sum('outstanding_balance')
    )['amount'] or Decimal('0')
    total_outstanding = basic_metrics.get('total_outstanding') or Decimal('0')
    par_ratio = (portfolio_at_risk / total_outstanding * 100) if total_outstanding > 0 else 0
    default_rate = (
        (status_breakdown['defaulted']['count'] / total_loans) * 100
        if total_loans > 0
        else 0
    )
    completion_rate = (
        (status_breakdown['completed']['count'] / total_loans) * 100
        if total_loans > 0
        else 0
    )

    # Prepare data for export
    headers = ['Metric', 'Value']
    data = []

    # Basic metrics
    data.extend([
        ['Total Loans', total_loans],
        ['Total Disbursed', format_currency(basic_metrics.get('total_disbursed', 0))],
        ['Total Outstanding', format_currency(basic_metrics.get('total_outstanding', 0))],
        ['Average Loan Size', format_currency(basic_metrics.get('avg_loan_size', 0))],
        ['Total Interest Earned', format_currency(basic_metrics.get('total_interest_earned', 0))],
    ])

    # Risk metrics
    data.extend([
        ['', ''],  # Empty row
        ['RISK METRICS', ''],
        ['Portfolio at Risk', format_currency(portfolio_at_risk)],
        ['PAR Ratio (%)', f"{par_ratio:.2f}%"],
        ['Default Rate (%)', f"{default_rate:.2f}%"],
        ['Completion Rate (%)', f"{completion_rate:.2f}%"],
    ])

    # Status breakdown
    data.extend([
        ['', ''],  # Empty row
        ['STATUS BREAKDOWN', ''],
    ])

    for status, metrics in status_breakdown.items():
        label = status.replace('_', ' ').title()
        data.extend([
            [f"{label} - Count", metrics.get('count', 0)],
            [f"{label} - Amount", format_currency(metrics.get('amount', 0))],
            [f"{label} - Percentage", f"{metrics.get('percentage', 0):.2f}%"],
        ])

    filename = f"portfolio_analysis_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    title = "Loan Portfolio Analysis"

    return export_to_pdf(data, headers, filename, title)


@login_required
def export_overdue_loans_pdf(request):
    """Export overdue loans to PDF."""
    overdue_loans = Loan.objects.overdue().select_related('borrower', 'loan_type')

    headers = [
        'Loan Number', 'Borrower', 'Phone', 'Approved Amount',
        'Outstanding Balance', 'Days Overdue', 'Penalty Total', 'Last Payment Date'
    ]

    data = []
    for loan in overdue_loans:
        last_payment_date = Repayment.objects.filter(
            schedule__loan=loan
        ).order_by('-payment_date').values_list('payment_date', flat=True).first()
        penalty_total = loan.penalties.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        data.append([
            loan.loan_number,
            loan.borrower.get_full_name(),
            loan.borrower.phone_number,
            loan.amount_approved or loan.amount_requested,
            loan.outstanding_balance,
            loan.days_overdue,
            penalty_total,
            last_payment_date,
        ])

    filename = f"overdue_loans_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    title = "Overdue Loans Report"

    return export_to_pdf(data, headers, filename, title)


@login_required
def export_overdue_loans_excel(request):
    """Export overdue loans to Excel."""
    overdue_loans = Loan.objects.overdue().select_related('borrower', 'loan_type')

    headers = [
        'Loan Number', 'Borrower', 'Phone', 'Email', 'Approved Amount',
        'Outstanding Balance', 'Days Overdue', 'Penalty Total', 'Last Payment Date',
        'Next Payment Due', 'Loan Officer', 'District', 'Region'
    ]

    data = []
    for loan in overdue_loans:
        last_payment_date = Repayment.objects.filter(
            schedule__loan=loan
        ).order_by('-payment_date').values_list('payment_date', flat=True).first()
        next_payment_due = loan.repayment_schedules.filter(
            status__in=[
                RepaymentStatusChoices.PENDING,
                RepaymentStatusChoices.DUE,
                RepaymentStatusChoices.PARTIAL,
                RepaymentStatusChoices.MISSED,
            ]
        ).order_by('due_date').values_list('due_date', flat=True).first()
        penalty_total = loan.penalties.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        data.append([
            loan.loan_number,
            loan.borrower.get_full_name(),
            loan.borrower.phone_number,
            loan.borrower.email,
            loan.amount_approved or loan.amount_requested,
            loan.outstanding_balance,
            loan.days_overdue,
            penalty_total,
            last_payment_date,
            next_payment_due,
            loan.loan_officer,
            loan.borrower.district,
            loan.borrower.region,
        ])

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
        active_loans = loans.filter(status=LoanStatusChoices.ACTIVE)
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


@login_required
def borrower_search_api(request):
    """API endpoint to search borrowers with active loans."""
    query = request.GET.get('q', '').strip()
    has_loans = request.GET.get('has_loans', 'true').lower() == 'true'
    
    try:
        from apps.borrowers.models import BorrowerStatus
        from apps.core.models import LoanStatusChoices
        
        borrowers = Borrower.objects.filter(status=BorrowerStatus.ACTIVE)
        
        if has_loans:
            # Filter borrowers who have loans that can receive repayments
            # Since approved loans are auto-disbursed, we only need disbursed and active
            active_loan_statuses = [
                LoanStatusChoices.DISBURSED,   # Standard disbursed loans
                LoanStatusChoices.ACTIVE,      # Active loans
            ]
            borrowers = borrowers.filter(
                loans__status__in=active_loan_statuses
            ).distinct()
        
        if query:
            borrowers = borrowers.filter(
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query) |
                Q(borrower_id__icontains=query) |
                Q(phone_number__icontains=query)
            )
        
        borrowers_data = []
        for borrower in borrowers.select_related('branch')[:20]:  # Limit to 20 results
            borrowers_data.append({
                'id': borrower.id,
                'full_name': borrower.get_full_name(),
                'identifier': borrower.borrower_id,
                'member_id': borrower.borrower_id,
                'phone': borrower.phone_number,
                'branch': borrower.branch.name if borrower.branch else 'N/A'
            })
        
        return JsonResponse({
            'success': True,
            'borrowers': borrowers_data,
            'count': len(borrowers_data),
            'has_loans_filter': has_loans
        })
        
    except Exception as e:
        import traceback
        print(f"Error in borrower_search_api: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': str(e),
            'error_type': 'server_error'
        })


@login_required
def borrowers_with_loans_api(request):
    """API endpoint to fetch all borrowers with active loans."""
    try:
        from apps.borrowers.models import BorrowerStatus
        from apps.core.models import LoanStatusChoices
        
        # Include all loan statuses that can receive repayments
        # Since approved loans are auto-disbursed, we only need disbursed and active
        active_loan_statuses = [
            LoanStatusChoices.DISBURSED,   # Standard disbursed loans
            LoanStatusChoices.ACTIVE,      # Active loans
        ]
        
        borrowers = Borrower.objects.filter(
            status=BorrowerStatus.ACTIVE,
            loans__status__in=active_loan_statuses
        ).distinct().select_related('branch')[:50]  # Limit to 50 results
        
        borrowers_data = []
        for borrower in borrowers:
            borrowers_data.append({
                'id': borrower.id,
                'full_name': borrower.get_full_name(),
                'identifier': borrower.borrower_id,
                'member_id': borrower.borrower_id,
                'phone': borrower.phone_number,
                'branch': borrower.branch.name if borrower.branch else 'N/A'
            })
        
        return JsonResponse({
            'success': True,
            'borrowers': borrowers_data,
            'count': len(borrowers_data)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in borrowers_with_loans_api: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': str(e),
            'error_type': 'server_error'
        })


@login_required
def borrower_loans_api(request, borrower_id):
    """API endpoint to fetch active loans for a specific borrower."""
    try:
        from apps.borrowers.models import BorrowerStatus
        from apps.core.models import LoanStatusChoices
        
        borrower = get_object_or_404(Borrower, id=borrower_id, status=BorrowerStatus.ACTIVE)
        
        # Include all loan statuses that can receive repayments
        # Since approved loans are auto-disbursed, we only need disbursed and active
        active_loan_statuses = [
            LoanStatusChoices.DISBURSED,   # Standard disbursed loans
            LoanStatusChoices.ACTIVE,      # Active loans
        ]
        
        loans = Loan.objects.filter(
            borrower=borrower,
            status__in=active_loan_statuses
        ).select_related('loan_type').order_by('-disbursement_date')
        
        loans_data = []
        for loan in loans:
            # Calculate penalty balance from related penalties
            from .models import Penalty
            penalty_balance = Penalty.objects.filter(
                loan=loan,
                status=PenaltyStatusChoices.APPLIED
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # Handle different loan statuses for display
            status_display = loan.get_status_display() if hasattr(loan, 'get_status_display') else loan.status
            
            loans_data.append({
                'id': loan.id,
                'disbursement_date': loan.disbursement_date.isoformat() if loan.disbursement_date else loan.application_date.isoformat(),
                'amount': float(loan.amount_approved or loan.amount_requested or 0),
                'interest_amount': float(loan.total_interest or 0),
                'penalty_balance': float(penalty_balance),
                'outstanding_balance': float(loan.outstanding_balance or loan.total_amount or 0),
                'loan_type': loan.loan_type.name if loan.loan_type else 'N/A',
                'status': loan.status,
                'status_display': status_display
            })
        
        return JsonResponse({
            'success': True,
            'loans': loans_data,
            'count': len(loans_data)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in borrower_loans_api: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': str(e),
            'error_type': 'server_error'
        })
