from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import F, Q, Count, Sum, Avg, OuterRef, Subquery
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta

# Django Tables2 and Filters
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin
# from django_filters.views import FilterView  # Will be enabled after package installation
from django.views.generic.list import ListView
from django.views.decorators.http import require_http_methods


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
    RepaymentForm, GroupRepaymentForm, LoanApprovalForm, LoanDisbursementForm,
    PenaltyForm, WrittenOffLoanForm, OldLoanImportForm, InterestCalculatorForm,
    RolloverForm
)

# Tables and Filters
from .tables import RepaidLoansTable, ExpectedRepaymentsTable, DisbursedLoansTable, NonPerformingLoansTable
# from .filters import LoanFilter, LoanBaseFilter, RepaymentScheduleFilter  # Will be enabled after package installation

# Export utilities
from apps.core.utils.export_utils import export_to_pdf, export_to_excel
from apps.core.utils.analytics_utils import format_currency

# =============================================================================
# CLASS-BASED VIEWS FOR TABLES AND FILTERING
# =============================================================================


def _require_admin_access(request):
    """Restrict sensitive loan state changes to elevated roles."""
    role = getattr(request.user, 'role', None)
    if role in {'admin', 'manager'}:
        return None

    if any([
        getattr(request.user, 'is_admin', False),
        getattr(request.user, 'is_staff', False),
        getattr(request.user, 'is_superuser', False),
    ]):
        return None

    messages.error(request, 'Access denied. Admin privileges required.')
    return redirect('core:dashboard')


def _has_elevated_access(user):
    """Return True for users allowed to view global approval queues."""
    role = getattr(user, 'role', None)
    if role in {'admin', 'manager'}:
        return True
    return any([
        getattr(user, 'is_admin', False),
        getattr(user, 'is_staff', False),
        getattr(user, 'is_superuser', False),
    ])

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
        
        # Optimize: Get all category counts in single query using annotations
        npl_loans = Loan.objects.non_performing()
        all_loans = Loan.objects.filter(
            status__in=[LoanStatusChoices.DISBURSED, LoanStatusChoices.ACTIVE]
        )
        
        # Use aggregations to reduce query count from 10+ to 2
        npl_stats = npl_loans.aggregate(
            total_count=Count('id'),
            total_amount=Sum('outstanding_balance'),
            total_provision=Sum('npl_provision_amount'),
            watch_count=Count('id', filter=Q(npl_category=NPLCategoryChoices.WATCH)),
            substandard_count=Count('id', filter=Q(npl_category=NPLCategoryChoices.SUBSTANDARD)),
            doubtful_count=Count('id', filter=Q(npl_category=NPLCategoryChoices.DOUBTFUL)),
            loss_count=Count('id', filter=Q(npl_category=NPLCategoryChoices.LOSS))
        )
        
        portfolio_stats = all_loans.aggregate(
            total_portfolio=Sum('outstanding_balance')
        )
        
        total_portfolio = portfolio_stats['total_portfolio'] or Decimal('0')
        total_npl_amount = npl_stats['total_amount'] or 0
        
        # NPL Ratio
        npl_ratio = (Decimal(str(total_npl_amount)) / Decimal(str(total_portfolio)) * 100) if total_portfolio > 0 else 0
        
        context.update({
            'title': 'Non-Performing Loans',
            'total_npl_count': npl_stats['total_count'] or 0,
            'total_npl_amount': total_npl_amount,
            'npl_ratio': round(npl_ratio, 2),
            'total_portfolio': total_portfolio,
            'total_provision': npl_stats['total_provision'] or 0,
            'watch_count': npl_stats['watch_count'] or 0,
            'substandard_count': npl_stats['substandard_count'] or 0,
            'doubtful_count': npl_stats['doubtful_count'] or 0,
            'loss_count': npl_stats['loss_count'] or 0,
            'npl_status_choices': NPLStatusChoices.choices,
        })
        return context


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_repayment_schedule(loan):
    """Generate repayment schedule for a disbursed loan with proper error handling."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Use model method if available (preferred - has all guards)
        if hasattr(loan, "generate_repayment_schedule") and callable(getattr(loan, "generate_repayment_schedule")):
            loan.generate_repayment_schedule()
            logger.info(f'Repayment schedule generated for loan {loan.loan_number} using model method')
            return
    except Exception as e:
        logger.error(f'Model method failed for loan {loan.loan_number}: {str(e)}')
        # Fall through to manual method below

    # Fallback to manual generation
    try:
        if not loan.disbursement_date:
            logger.error(f'Cannot generate schedule: disbursement_date is missing for loan {loan.loan_number}')
            raise ValueError("Disbursement date is required to generate repayment schedule")
        
        if loan.duration_months <= 0:
            logger.error(f'Cannot generate schedule: invalid duration_months ({loan.duration_months}) for loan {loan.loan_number}')
            raise ValueError(f"Invalid duration months: {loan.duration_months}")
        
        if loan.total_amount <= 0:
            logger.error(f'Cannot generate schedule: invalid total_amount ({loan.total_amount}) for loan {loan.loan_number}')
            raise ValueError(f"Invalid total amount: {loan.total_amount}")
        
        installment_amount = loan.total_amount / loan.duration_months
        current_date = loan.disbursement_date

        schedule_count = 0
        for i in range(loan.duration_months):
            due_date = current_date + relativedelta(months=i + 1)
            RepaymentSchedule.objects.create(
                loan=loan,
                due_date=due_date,
                amount_due=installment_amount,
                installment_number=i + 1,
                is_group=hasattr(loan, 'group_loan')
            )
            schedule_count += 1
        
        logger.info(f'Generated {schedule_count} repayment schedules for loan {loan.loan_number}')
    except Exception as e:
        logger.error(f'Failed to generate repayment schedule for loan {loan.loan_number}: {str(e)}', exc_info=True)
        raise


# =============================================================================
# LOAN MANAGEMENT VIEWS
# =============================================================================


@login_required
def nearing_last_installments(request):
    nearing = RepaymentSchedule.objects.filter(installment_number__gte=F('loan__duration_months') - 1)
    return render(request, 'loans/nearing_last.html', {'schedules': nearing})

@login_required
def loan_repayments(request, loan_id):
    from .tables import LoanRepaymentsTable
    
    loan = get_object_or_404(Loan, pk=loan_id)
    repayments = Repayment.objects.filter(schedule__loan=loan)
    
    # Create table
    table = LoanRepaymentsTable(repayments)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)
    
    return render(request, 'loans/loan_repayments.html', {
        'loan': loan, 
        'repayments': repayments,
        'table': table
    })

@login_required
def loan_detail(request, loan_id):
    """View to display detailed information about a specific loan."""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get repayment schedule
    schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('due_date')
    
    # Get actual repayments
    repayments = Repayment.objects.filter(schedule__loan=loan).order_by('-payment_date')
    
    # Calculate loan statistics
    total_expected = schedule.aggregate(total=Sum('amount_due'))['total'] or Decimal('0')
    total_paid = repayments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    outstanding_balance = max(total_expected - total_paid, Decimal('0'))
    
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

            # Notify admin/manager users that a new loan requires approval.
            try:
                from apps.notifications.models import NotificationType
                from apps.notifications.utils import create_notifications_for_users

                recipients = CustomUser.objects.filter(
                    role__in=['admin', 'manager'],
                    is_active=True,
                ).exclude(id=request.user.id)

                create_notifications_for_users(
                    recipients=recipients,
                    actor=request.user,
                    title='New Loan Pending Approval',
                    message=f'Loan {loan.loan_number} for {loan.borrower.get_full_name()} was submitted and is pending approval.',
                    notification_type=NotificationType.APPROVAL,
                    target_url='/loans/pending/',
                )
            except Exception:
                pass

            messages.success(request, f'Loan {loan.loan_number} submitted successfully for approval.')
            return redirect('loans:loan_list')
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
@transaction.atomic
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
            members = list(loan_form.cleaned_data['group'].members.all())
            member_count = len(members)
            if member_count == 0:
                messages.error(request, 'Selected group has no members.')
                return redirect('loans:add_group_loan')

            responsibility_share = Decimal('100.00') / Decimal(str(member_count))
            for member in members:
                GroupLoanMember.objects.create(
                    group_loan=group_loan,
                    borrower=member,
                    responsibility_share=responsibility_share
                )

            # Notify admin/manager users that a new group loan requires approval.
            try:
                from apps.notifications.models import NotificationType
                from apps.notifications.utils import create_notifications_for_users

                recipients = CustomUser.objects.filter(
                    role__in=['admin', 'manager'],
                    is_active=True,
                ).exclude(id=request.user.id)

                create_notifications_for_users(
                    recipients=recipients,
                    actor=request.user,
                    title='New Group Loan Pending Approval',
                    message=f'Group loan {loan.loan_number} for {group_loan.group.group_name} was submitted and is pending approval.',
                    notification_type=NotificationType.APPROVAL,
                    target_url='/loans/pending/',
                )
            except Exception:
                pass
            
            messages.success(request, f'Group loan {loan.loan_number} submitted successfully for approval.')
            return redirect('loans:loan_list')
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
def edit_loan(request, loan_id):
    """Edit a pending individual loan application."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    loan = get_object_or_404(Loan, pk=loan_id)

    # Group loan editing is handled in its dedicated workflow.
    try:
        if hasattr(loan, 'group_loan') and loan.group_loan is not None:
            messages.error(request, 'Group loans should be updated from the group loan workflow.')
            return redirect('loans:loan_detail', loan_id=loan.id)
    except GroupLoan.DoesNotExist:
        pass

    if loan.status in {LoanStatusChoices.COMPLETED, LoanStatusChoices.WRITTEN_OFF}:
        messages.error(request, 'Completed or written-off loans cannot be edited.')
        return redirect('loans:loan_detail', loan_id=loan.id)

    if request.method == 'POST':
        form = ComprehensiveLoanForm(request.POST, request.FILES, instance=loan)
        if form.is_valid():
            updated_loan = form.save(commit=False)
            updated_loan.updated_by = request.user
            updated_loan.save()
            messages.success(request, f'Loan {updated_loan.loan_number} updated successfully.')
            return redirect('loans:loan_detail', loan_id=updated_loan.id)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ComprehensiveLoanForm(instance=loan)

    context = {
        'form': form,
        'loan': loan,
        'title': f'Edit Loan {loan.loan_number}',
        'page_title': 'Edit Loan Application',
    }
    return render(request, 'loans/edit_loan.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def delete_loan(request, loan_id):
    """Soft-delete a loan by rejecting it before disbursement."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    loan = get_object_or_404(Loan, pk=loan_id)

    if loan.status not in {LoanStatusChoices.PENDING, LoanStatusChoices.APPROVED}:
        messages.error(request, 'Only pending or approved loans can be deleted.')
        return redirect('loans:loan_detail', loan_id=loan.id)

    if request.method == 'POST':
        reason = request.POST.get('deletion_reason', '').strip() or 'Deleted by admin/manager'
        loan.status = LoanStatusChoices.REJECTED
        loan.rejection_reason = reason
        loan.rejected_by = request.user
        loan.rejection_date = timezone.now().date()
        loan.updated_by = request.user
        loan.save(update_fields=['status', 'rejection_reason', 'rejected_by', 'rejection_date', 'updated_by', 'updated_at'])

        messages.success(request, f'Loan {loan.loan_number} deleted successfully.')
        return redirect('loans:loan_list')

    return render(request, 'loans/delete_loan.html', {'loan': loan})


@login_required
def loan_approval(request, loan_id):
    """Approve a pending loan. Disbursement is handled separately."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    loan = get_object_or_404(Loan, pk=loan_id, status=LoanStatusChoices.PENDING)
    
    if request.method == 'POST':
        form = LoanApprovalForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)

            # Approval only; disbursement is a separate workflow step.
            loan.status = LoanStatusChoices.APPROVED
            loan.approved_by = request.user
            loan.approval_date = timezone.now().date()
            loan.save()

            # Notify the loan creator that approval has been completed.
            try:
                from apps.notifications.models import NotificationType
                from apps.notifications.utils import create_notification

                if loan.created_by and loan.created_by_id != request.user.id:
                    create_notification(
                        recipient=loan.created_by,
                        actor=request.user,
                        title='Loan Approved',
                        message=f'Loan {loan.loan_number} has been approved and is ready for disbursement.',
                        notification_type=NotificationType.SUCCESS,
                        target_url=f'/loans/{loan.id}/',
                    )
            except Exception:
                pass

            messages.success(
                request,
                f'Loan {loan.loan_number} approved successfully. Proceed to disbursement when ready.'
            )
            return redirect('loans:approved_loans')
    else:
        form = LoanApprovalForm(instance=loan)

    return render(request, 'loans/loan_approval.html', {
        'form': form,
        'loan': loan,
        'title': f'Approve Loan {loan.loan_number}'
    })


@login_required
@require_http_methods(["POST"])
def loan_rejection(request, loan_id):
    """Reject a pending loan."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

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

        # Notify the loan creator about rejection.
        try:
            from apps.notifications.models import NotificationType
            from apps.notifications.utils import create_notification

            if loan.created_by and loan.created_by_id != request.user.id:
                create_notification(
                    recipient=loan.created_by,
                    actor=request.user,
                    title='Loan Rejected',
                    message=f'Loan {loan.loan_number} was rejected. Reason: {rejection_reason}',
                    notification_type=NotificationType.ERROR,
                    target_url=f'/loans/{loan.id}/',
                )
        except Exception:
            pass

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
        except ImportError as e:
            return JsonResponse({
                'success': True, 
                'message': f'Loan {loan.loan_number} rejected successfully!',
                'warning': f'SMS service unavailable: {str(e)}',
                'redirect_url': '/loans/pending/'
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'SMS notification failed for loan {loan.loan_number}: {str(e)}')
            return JsonResponse({
                'success': True, 
                'message': f'Loan {loan.loan_number} rejected successfully!',
                'warning': 'SMS notification failed',
                'redirect_url': '/loans/pending/'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@transaction.atomic
def loan_disbursement(request, loan_id):
    """Disburse an approved loan."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    loan = get_object_or_404(Loan, pk=loan_id, status=LoanStatusChoices.APPROVED)
    
    if request.method == 'POST':
        form = LoanDisbursementForm(request.POST, loan=loan)
        if form.is_valid():
            try:
                disbursement = form.save(commit=False)
                disbursement.loan = loan
                disbursement.disbursed_by = request.user
                disbursement.save()
                
                # Update loan status and generate repayment schedule
                loan.status = LoanStatusChoices.DISBURSED
                loan.disbursement_date = disbursement.disbursement_date
                loan.disbursed_by = request.user
                
                # Validate loan before saving
                try:
                    loan.full_clean()
                except Exception as validation_error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Loan validation failed during disbursement: {str(validation_error)}')
                    messages.error(request, f'Loan validation failed: {str(validation_error)}')
                    return render(request, 'loans/loan_disbursement.html', {
                        'form': form,
                        'loan': loan,
                        'title': f'Disburse Loan {loan.loan_number}'
                    })
                
                loan.save()

                # Notify loan creator that disbursement is complete.
                try:
                    from apps.notifications.models import NotificationType
                    from apps.notifications.utils import create_notification

                    if loan.created_by and loan.created_by_id != request.user.id:
                        create_notification(
                            recipient=loan.created_by,
                            actor=request.user,
                            title='Loan Disbursed',
                            message=f'Loan {loan.loan_number} has been disbursed successfully.',
                            notification_type=NotificationType.SUCCESS,
                            target_url=f'/loans/{loan.id}/',
                        )
                except Exception:
                    pass
                
                # Verify loan was saved with DISBURSED status
                refreshed_loan = Loan.objects.get(pk=loan.pk)
                if refreshed_loan.status != LoanStatusChoices.DISBURSED:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Loan status not updated to DISBURSED. Current status: {refreshed_loan.status}')
                    messages.error(request, 'Error: Loan status was not properly updated to DISBURSED.')
                    return render(request, 'loans/loan_disbursement.html', {
                        'form': form,
                        'loan': loan,
                        'title': f'Disburse Loan {loan.loan_number}'
                    })
                
                # Generate repayment schedule
                try:
                    _generate_repayment_schedule(loan)
                except Exception as schedule_error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Failed to generate repayment schedule for loan {loan.loan_number}: {str(schedule_error)}')
                    messages.warning(request, f'Loan disbursed but repayment schedule generation failed: {str(schedule_error)}')
                
                # Send SMS notification
                try:
                    from apps.core.sms_service import sms_service
                    sms_result = sms_service.send_loan_disbursement(loan)
                    if sms_result.get('success'):
                        messages.success(request, f'Loan {loan.loan_number} disbursed successfully! SMS notification sent.')
                    else:
                        messages.success(request, f'Loan {loan.loan_number} disbursed successfully!')
                        messages.warning(request, f'SMS notification failed: {sms_result.get("error", "Unknown error")}')
                except ImportError as e:
                    messages.success(request, f'Loan {loan.loan_number} disbursed successfully!')
                    messages.info(request, 'SMS service unavailable')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'SMS notification failed for loan {loan.loan_number}: {str(e)}')
                    messages.success(request, f'Loan {loan.loan_number} disbursed successfully!')

                return redirect('loans:disbursed_loans')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Unexpected error during loan disbursement: {str(e)}', exc_info=True)
                messages.error(request, f'Disbursement failed: {str(e)}. Please contact support.')
                # Mark transaction for rollback will happen automatically due to exception
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
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
@transaction.atomic
def record_repayment(request, schedule_id):
    """Record an individual repayment using form validation."""
    schedule = get_object_or_404(RepaymentSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = RepaymentForm(request.POST, schedule=schedule)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.schedule = schedule
            repayment.received_by = request.user
            repayment.status = RepaymentStatusChoices.PAID
            repayment.save()
            
            # Update schedule totals and status
            schedule.amount_paid = (schedule.amount_paid or Decimal('0')) + repayment.amount_paid
            schedule.save(update_fields=['amount_paid'])
            schedule.update_status()
            
            # Update loan outstanding balance
            loan = schedule.loan
            
            # DEBUG: Log calculation details
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"REPAYMENT DEBUG - Loan {loan.loan_number}:")
            logger.warning(f"  Loan.total_amount: {loan.total_amount}")
            logger.warning(f"  Loan.total_paid (before calc): {loan.total_paid}")
            logger.warning(f"  New repayment amount: {repayment.amount_paid}")
            
            # Get all repayments for this loan and calculate total
            repayments_qs = Repayment.objects.filter(schedule__loan=loan, status=RepaymentStatusChoices.PAID)
            all_repayments = list(repayments_qs.values('id', 'schedule_id', 'amount_paid', 'status'))
            logger.warning(f"  All PAID repayments for loan:")
            for r in all_repayments:
                logger.warning(f"    - ID: {r['id']}, Amount: {r['amount_paid']}")
            
            total_paid = repayments_qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
            logger.warning(f"  Aggregated total from query: {total_paid}")
            
            # Calculate outstanding balance
            loan.total_paid = total_paid
            loan.outstanding_balance = max(loan.total_amount - total_paid, Decimal('0.00'))
            
            logger.warning(f"  Calculated outstanding: {loan.total_amount} - {total_paid} = {loan.outstanding_balance}")
            
            # Update loan status if fully paid
            if loan.outstanding_balance <= Decimal('0.00'):
                loan.status = LoanStatusChoices.COMPLETED
                loan.outstanding_balance = Decimal('0.00')
            elif loan.status in [LoanStatusChoices.PENDING, LoanStatusChoices.APPROVED]:
                loan.status = LoanStatusChoices.ACTIVE
            
            loan.save(update_fields=['total_paid', 'outstanding_balance', 'status'])
            logger.warning(f"  Loan saved with total_paid={loan.total_paid}, outstanding={loan.outstanding_balance}")
            
            messages.success(request, f'Repayment of Tsh {repayment.amount_paid:,.2f} recorded successfully!')
            return redirect('loans:loan_repayments', loan_id=loan.id)
    else:
        form = RepaymentForm(schedule=schedule)

    return render(request, 'loans/record_repayment.html', {
        'form': form,
        'schedule': schedule,
        'title': f'Record Repayment - {schedule.loan.loan_number}'
    })


@login_required
@transaction.atomic
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
            
            # Get all paid repayments for this loan and calculate total
            repayments_qs = Repayment.objects.filter(schedule__loan=loan, status=RepaymentStatusChoices.PAID)
            total_paid = repayments_qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
            
            # Calculate outstanding balance
            loan.total_paid = total_paid
            loan.outstanding_balance = max(loan.total_amount - total_paid, Decimal('0.00'))
            
            # Update loan status if fully paid
            if loan.outstanding_balance <= Decimal('0.00'):
                loan.status = LoanStatusChoices.COMPLETED
                loan.outstanding_balance = Decimal('0.00')
            elif loan.status in [LoanStatusChoices.PENDING, LoanStatusChoices.APPROVED]:
                loan.status = LoanStatusChoices.ACTIVE
            
            loan.save(update_fields=['total_paid', 'outstanding_balance', 'status'])
            
            messages.success(request, f'Group repayment of Tsh {repayment.amount_paid:,.2f} recorded successfully!')
            return redirect('loans:loan_repayments', loan_id=loan.id)
    else:
        form = GroupRepaymentForm(group=group)

    return render(request, 'loans/record_group_repayment.html', {
        'form': form,
        'schedule': schedule,
        'group': group,
        'title': f'Record Group Repayment - {schedule.loan.loan_number}'
    })


@login_required
@transaction.atomic
def rollover_repayment(request, schedule_id):
    """Roll over a repayment to a new due date."""
    schedule = get_object_or_404(RepaymentSchedule, id=schedule_id)

    if request.method == 'POST':
        form = RolloverForm(request.POST)
        if form.is_valid():
            # Mark original as rolled over
            schedule.status = RepaymentStatusChoices.ROLLED_OVER
            schedule.save()

            # Create new schedule from the remaining unpaid amount plus fee.
            remaining_due = max((schedule.amount_due or Decimal('0')) - (schedule.amount_paid or Decimal('0')), Decimal('0'))
            rollover_amount_due = remaining_due + form.cleaned_data['rollover_fee']

            # Create new schedule
            RepaymentSchedule.objects.create(
                loan=schedule.loan,
                due_date=form.cleaned_data['new_due_date'],
                amount_due=rollover_amount_due,
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
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta
    
    missed = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.MISSED
    ).select_related('loan__borrower').order_by('due_date', 'loan__loan_number')

    # Calculate statistics
    total_missed_amount = missed.aggregate(Sum('amount_due'))['amount_due__sum'] or Decimal('0')
    
    # This month's missed schedules
    this_month = timezone.now().replace(day=1).date()
    this_month_missed = missed.filter(due_date__gte=this_month).count()
    
    # Unique borrowers with missed schedules
    unique_borrowers = missed.values('loan__borrower').distinct().count()

    return render(request, 'loans/missed_schedules.html', {
        'missed': missed,
        'total_missed_amount': total_missed_amount,
        'this_month_missed': this_month_missed,
        'unique_borrowers': unique_borrowers,
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
    from .tables import OutstandingLoansTable
    from django.db.models import Sum
    from datetime import date, timedelta
    
    # Get all loans with outstanding balance
    loans_queryset = Loan.objects.filter(
        outstanding_balance__gt=0
    ).select_related('borrower', 'loan_type').prefetch_related('repayment_schedules')
    
    # Apply filters
    filter_instance = OutstandingLoansFilter(request.GET, queryset=loans_queryset)
    filtered_loans = filter_instance.qs
    
    # Create table
    table = OutstandingLoansTable(filtered_loans)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)
    
    # Calculate statistics on the queryset
    total_outstanding = filtered_loans.aggregate(
        Sum('outstanding_balance')
    )['outstanding_balance__sum'] or 0
    
    total_count = filtered_loans.count()
    
    # Calculate risk distribution by iterating through schedules
    current_loans = 0
    overdue_1_30 = 0
    overdue_31_90 = 0
    overdue_90_plus = 0
    overdue_loans = 0
    overdue_amount = Decimal('0')
    
    today = timezone.now().date()
    
    for loan in filtered_loans:
        # Get unpaid schedules for this loan
        unpaid_schedules = loan.repayment_schedules.filter(
            status__in=[RepaymentStatusChoices.PENDING, RepaymentStatusChoices.MISSED]
        )
        
        if not unpaid_schedules.exists():
            current_loans += 1
            continue
        
        # Get oldest overdue schedule
        oldest_overdue = unpaid_schedules.filter(due_date__lt=today).order_by('due_date').first()
        
        if oldest_overdue:
            days_overdue = (today - oldest_overdue.due_date).days
            overdue_loans += 1
            overdue_amount += loan.outstanding_balance
            
            if 1 <= days_overdue <= 30:
                overdue_1_30 += 1
            elif 31 <= days_overdue <= 90:
                overdue_31_90 += 1
            else:
                overdue_90_plus += 1
        else:
            # Has pending schedules but none are overdue yet
            current_loans += 1
    
    # Portfolio at risk calculation (loans more than 30 days overdue)
    portfolio_at_risk = (overdue_31_90 + overdue_90_plus) / total_count * 100 if total_count > 0 else 0
    
    context = {
        'table': table,
        'filter': filter_instance,
        'total_outstanding': total_outstanding,
        'total_loans': total_count,
        'overdue_amount': overdue_amount,
        'overdue_loans': overdue_loans,
        'current_loans': current_loans,
        'overdue_1_30': overdue_1_30,
        'overdue_31_90': overdue_31_90,
        'overdue_90_plus': overdue_90_plus,
        'portfolio_at_risk': round(portfolio_at_risk, 1),
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
    total_defaulted_amount = loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or Decimal('0')

    # This month's new defaults
    this_month = timezone.now().replace(day=1)
    new_defaults_this_month = loans.filter(
        status_updated_date__gte=this_month
    ).count() if hasattr(Loan, 'status_updated_date') else loans.filter(
        updated_at__gte=this_month
    ).count()

    # Critical defaults (over 365 days overdue)
    critical_cutoff = timezone.now().date() - timedelta(days=365)
    critical_defaults = RepaymentSchedule.objects.filter(
        loan__status=LoanStatusChoices.DEFAULTED,
        due_date__lt=critical_cutoff,
        status=RepaymentStatusChoices.PENDING
    ).values('loan').distinct().count()

    # Default trend vs last month
    last_month = this_month - timedelta(days=1)
    last_month_start = last_month.replace(day=1)
    defaults_last_month = loans.filter(
        updated_at__gte=last_month_start,
        updated_at__lt=this_month
    ).count()
    default_trend = ((new_defaults_this_month - defaults_last_month) / defaults_last_month * 100) if defaults_last_month > 0 else 0

    # Recovery rate (amount recovered from defaulted loans)
    recovered_amount = Repayment.objects.filter(
        schedule__loan__status=LoanStatusChoices.DEFAULTED
    ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
    recovery_rate = (recovered_amount / total_defaulted_amount * 100) if total_defaulted_amount > 0 else 0
    recovered_this_month = Repayment.objects.filter(
        schedule__loan__status=LoanStatusChoices.DEFAULTED,
        payment_date__gte=this_month
    ).count()

    # Legal actions (placeholder - would need a LegalAction model)
    legal_actions = 0  # Implement if you have a legal actions model
    pending_legal = 0

    context = {
        'loans': loans,
        'total_defaulted': total_defaulted,
        'total_defaulted_amount': total_defaulted_amount,
        'new_defaults_this_month': new_defaults_this_month,
        'critical_defaults': critical_defaults,
        'default_trend': round(default_trend, 1),
        'recovery_rate': round(recovery_rate, 2),
        'recovered_this_month': recovered_this_month,
        'legal_actions': legal_actions,
        'pending_legal': pending_legal,
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
        'total_amount': loans.aggregate(Sum('amount_approved'))['amount_approved__sum'] or Decimal('0'),
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
@require_http_methods(["POST"])
def clear_penalties(request):
    """Clear all applied penalties."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

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
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

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
    from .tables import PortfolioAtRiskTable
    
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
    at_risk_amount = Decimal('0')

    for loan in loans:
        if loan.oldest_overdue_due_date:
            days = (today - loan.oldest_overdue_due_date).days

            # PAR = 6 to 30 days overdue
            if 6 <= days <= 30:
                loan.days_overdue = days
                par_loans.append(loan)
                at_risk_amount += loan.outstanding_balance

    # Create table
    table = PortfolioAtRiskTable(par_loans)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    total_portfolio = Loan.objects.filter(
        status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
    ).aggregate(Sum("outstanding_balance"))["outstanding_balance__sum"] or Decimal('0')

    risk_percentage = (
        (at_risk_amount / total_portfolio) * 100
        if total_portfolio > 0 else 0
    )

    return render(request, "loans/portfolio_at_risk.html", {
        "loans": par_loans,
        "table": table,
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
    total_portfolio_value = portfolio.aggregate(Sum('total_disbursed'))['total_disbursed__sum'] or Decimal('0')
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
    today = timezone.localdate()
    data_by_gender = {}

    borrowers = Borrower.objects.all().prefetch_related('loans')
    for borrower in borrowers:
        gender = borrower.gender or 'Unknown'
        if gender not in data_by_gender:
            data_by_gender[gender] = {
                'gender': gender,
                'total': 0,
                'under_25': 0,
                'between_25_40': 0,
                'above_40': 0,
                'total_loans': 0,
                'total_amount': Decimal('0'),
            }

        row = data_by_gender[gender]
        row['total'] += 1

        if borrower.date_of_birth:
            age = today.year - borrower.date_of_birth.year
            if (today.month, today.day) < (borrower.date_of_birth.month, borrower.date_of_birth.day):
                age -= 1
            if age < 25:
                row['under_25'] += 1
            elif age <= 40:
                row['between_25_40'] += 1
            else:
                row['above_40'] += 1

        borrower_loans = borrower.loans.all()
        row['total_loans'] += len(borrower_loans)
        row['total_amount'] += sum((loan.amount_approved or Decimal('0')) for loan in borrower_loans)

    data = list(data_by_gender.values())
    
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
    total_disbursed = Loan.objects.exclude(status__in=[LoanStatusChoices.PENDING, LoanStatusChoices.REJECTED]).aggregate(Sum('amount_approved'))['amount_approved__sum'] or Decimal('0')
    active_loans = Loan.objects.filter(status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED, LoanStatusChoices.APPROVED]).count()

    # Calculate repayment rate
    completed_loans = Loan.objects.filter(status=LoanStatusChoices.COMPLETED).count()
    repayment_rate = (completed_loans / total_loans * 100) if total_loans > 0 else 0

    # Enhanced monthly data - Get data for current year
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Monthly disbursement amounts - Include ALL loan statuses except pending/rejected
    disbursement_summary = Loan.objects.filter(
        disbursement_date__year=timezone.now().year
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
        payment_date__year=timezone.now().year,
        status='completed'
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total_amount=Sum('amount')
    ).order_by('month')

    # Monthly defaulted loan amounts
    defaulted_summary = Loan.objects.filter(
        status=LoanStatusChoices.DEFAULTED,
        disbursement_date__year=timezone.now().year
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

    # Portfolio-at-risk buckets based on oldest overdue installment per loan.
    today = timezone.localdate()
    overdue_statuses = [
        RepaymentStatusChoices.PENDING,
        RepaymentStatusChoices.DUE,
        RepaymentStatusChoices.PARTIAL,
        RepaymentStatusChoices.MISSED,
        RepaymentStatusChoices.DEFAULTED,
    ]
    oldest_overdue_due_date_sq = RepaymentSchedule.objects.filter(
        loan_id=OuterRef('pk'),
        due_date__lt=today,
        status__in=overdue_statuses,
    ).order_by('due_date').values('due_date')[:1]

    risk_loans = Loan.objects.filter(
        status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
    ).annotate(
        oldest_overdue_due_date=Subquery(oldest_overdue_due_date_sq)
    )

    risk_0_30 = 0
    risk_31_60 = 0
    risk_61_90 = 0
    risk_90_plus = 0
    for loan in risk_loans:
        if not loan.oldest_overdue_due_date:
            continue
        days_overdue = (today - loan.oldest_overdue_due_date).days
        if 1 <= days_overdue <= 30:
            risk_0_30 += 1
        elif 31 <= days_overdue <= 60:
            risk_31_60 += 1
        elif 61 <= days_overdue <= 90:
            risk_61_90 += 1
        elif days_overdue > 90:
            risk_90_plus += 1

    # Convert to percentages
    total_active = active_loans
    risk_percentages = [
        round((risk_0_30 / total_active * 100), 1) if total_active > 0 else 0,
        round((risk_31_60 / total_active * 100), 1) if total_active > 0 else 0,
        round((risk_61_90 / total_active * 100), 1) if total_active > 0 else 0,
        round((risk_90_plus / total_active * 100), 1) if total_active > 0 else 0,
    ]

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
@transaction.atomic
def create_group_schedule(request, group_loan_id):
    """Create repayment schedule for a group loan."""
    group_loan = get_object_or_404(GroupLoan, id=group_loan_id)
    loan = group_loan.loan

    if request.method == 'POST':
        try:
            # Validate installments parameter
            installments_param = request.POST.get('installments', '').strip()
            if not installments_param:
                raise ValueError('Installments field is required.')
            try:
                num_installments = int(installments_param)
            except ValueError:
                raise ValueError('Installments must be a valid integer.')
            
            if num_installments <= 0:
                raise ValueError('Installments must be greater than zero.')
            if num_installments > 360:  # Max 30 years
                raise ValueError('Installments cannot exceed 360 (30 years).')
            
            # Validate start_date parameter
            start_date_param = request.POST.get('start_date', '').strip()
            if not start_date_param:
                raise ValueError('Start date field is required.')
            try:
                start_date = timezone.datetime.strptime(
                    start_date_param, '%Y-%m-%d'
                ).date()
            except ValueError:
                raise ValueError('Start date must be in YYYY-MM-DD format.')
            
            # Validate start_date is not in the past
            if start_date < timezone.now().date():
                raise ValueError('Start date cannot be in the past.')
            
            # Validate loan parameters
            if not loan.total_amount or loan.total_amount <= 0:
                raise ValueError('Loan has invalid total amount.')
            
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

            messages.success(request, f'Group repayment schedule created successfully with {num_installments} installments!')
            return redirect('loans:group_loans')
            
        except ValueError as e:
            messages.error(request, f'Invalid input: {str(e)}')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error creating group schedule for loan {group_loan_id}: {str(e)}')
            messages.error(request, 'An unexpected error occurred while creating the schedule.')

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
                    if monthly_rate > 0:
                        emi = principal * (monthly_rate * (1 + monthly_rate)**n) / ((1 + monthly_rate)**n - 1)
                        total_amount = emi * n
                        total_interest = total_amount - principal
                        monthly_payment = emi
                    else:
                        total_amount = principal
                        total_interest = Decimal('0')
                        monthly_payment = principal / n
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
    # TODO: Implement portfolio summary view with:
    # - Portfolio breakdown by loan type
    # - Portfolio performance metrics
    # - Risk distribution across portfolios
    # - Growth trends by portfolio
    # For now, providing placeholder context
    portfolios = LoanType.objects.filter(is_active=True).annotate(
        total_loans=Count('loan'),
        total_amount=Sum('loan__amount_approved'),
        outstanding=Sum('loan__outstanding_balance'),
        avg_loan_size=Avg('loan__amount_approved')
    )
    
    return render(request, 'loans/summary_by_portfolio.html', {
        'title': 'Loan Summary by Portfolio',
        'portfolios': portfolios
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
    # Optimize: Get all data with single query using select_related
    overdue_loans = Loan.objects.overdue().select_related(
        'borrower', 'loan_type'
    ).prefetch_related('repayment_schedules', 'penalties')

    headers = [
        'Loan Number', 'Borrower', 'Phone', 'Email', 'Approved Amount',
        'Outstanding Balance', 'Days Overdue', 'Penalty Total', 'Last Payment Date',
        'Next Payment Due', 'Loan Officer', 'District', 'Region'
    ]

    data = []
    for loan in overdue_loans:
        # Get last payment date from prefetched relationships (no N+1 query)
        last_payment_date = None
        if hasattr(loan, '_prefetched_objects_cache'):
            # Use prefetched repayment schedules if available
            schedules = list(loan.repayment_schedules.all())
            if schedules:
                last_payment_date = max(
                    (s.repayments.values_list('payment_date', flat=True).last() 
                     for s in schedules if s.repayments.exists()),
                    default=None
                )
        
        if not last_payment_date:
            # Fallback: single query per loan (but prefetch helps)
            last_repayment = Repayment.objects.filter(
                schedule__loan=loan
            ).order_by('-payment_date').values_list('payment_date', flat=True).first()
            last_payment_date = last_repayment
        
        # Get next payment due date
        next_payment_due = loan.repayment_schedules.filter(
            status__in=[
                RepaymentStatusChoices.PENDING,
                RepaymentStatusChoices.DUE,
                RepaymentStatusChoices.PARTIAL,
                RepaymentStatusChoices.MISSED,
            ]
        ).order_by('due_date').values_list('due_date', flat=True).first()
        
        # Get penalty total from prefetched relationships
        penalty_total = Decimal('0')
        if hasattr(loan, '_prefetched_objects_cache'):
            penalty_total = sum(
                (p.amount for p in loan.penalties.filter(
                    status=PenaltyStatusChoices.APPLIED
                )),
                Decimal('0')
            )
        else:
            penalty_total = loan.penalties.filter(
                status=PenaltyStatusChoices.APPLIED
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

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
    from .tables import PenaltiesTable
    
    penalties = Penalty.objects.select_related('loan__borrower', 'schedule').filter(
        status=PenaltyStatusChoices.APPLIED
    )
    
    # Create table
    table = PenaltiesTable(penalties)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)
    
    return render(request, 'loans/penalties.html', {
        'penalties': penalties,
        'table': table,
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
    from django.db.models import Sum, Count
    from django.utils import timezone
    
    missed_schedules = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.MISSED
    ).select_related('loan__borrower').order_by('due_date', 'loan__loan_number')

    # Calculate statistics
    total_missed_amount = missed_schedules.aggregate(Sum('amount_due'))['amount_due__sum'] or Decimal('0')
    
    # This month's missed payments
    this_month = timezone.now().replace(day=1).date()
    this_month_missed = missed_schedules.filter(due_date__gte=this_month).count()
    
    # Unique borrowers with missed payments
    unique_borrowers = missed_schedules.values('loan__borrower').distinct().count()

    return render(request, 'loans/missed_payments.html', {
        'missed_payments': missed_schedules,
        'total_missed_amount': total_missed_amount,
        'this_month_missed': this_month_missed,
        'unique_borrowers': unique_borrowers,
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
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

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
def approved_loans_list(request):
    """List all approved loans awaiting disbursement."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    approved_loans = Loan.objects.filter(
        status=LoanStatusChoices.APPROVED
    ).select_related('borrower', 'loan_type', 'approved_by').order_by('-approval_date', '-created_at')

    approved_group_loans = GroupLoan.objects.filter(
        loan__status=LoanStatusChoices.APPROVED
    ).select_related('group', 'loan__loan_type', 'loan__approved_by').order_by('-loan__approval_date', '-loan__created_at')

    context = {
        'title': 'Approved Loans Ready for Disbursement',
        'approved_loans': approved_loans,
        'approved_group_loans': approved_group_loans,
        'total_approved': approved_loans.count() + approved_group_loans.count(),
    }

    return render(request, 'loans/approved_loans.html', context)


@login_required
def rejected_loans_list(request):
    """List rejected loans; officers see their own submissions, approvers see all."""
    rejected_loans = Loan.objects.filter(status=LoanStatusChoices.REJECTED).select_related(
        'borrower', 'loan_type', 'created_by', 'rejected_by'
    )

    if not _has_elevated_access(request.user):
        rejected_loans = rejected_loans.filter(created_by=request.user)

    rejected_loans = rejected_loans.order_by('-rejection_date', '-created_at')

    context = {
        'title': 'Rejected Loan Applications',
        'rejected_loans': rejected_loans,
    }

    return render(request, 'loans/rejected_loans.html', context)


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
        total_amount = loans.aggregate(Sum('amount_approved'))['amount_approved__sum'] or Decimal('0')
        outstanding = loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or Decimal('0')

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
def edit_group_loan(request, group_loan_id):
    """Edit a pending group loan application."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    group_loan = get_object_or_404(GroupLoan.objects.select_related('loan', 'group'), id=group_loan_id)
    loan = group_loan.loan

    if loan.status != LoanStatusChoices.PENDING:
        messages.error(request, 'Only pending group loan applications can be edited.')
        return redirect('loans:group_loans')

    if request.method == 'POST':
        payload = request.POST.copy()
        payload['group'] = str(group_loan.group.id)
        form = ComprehensiveGroupLoanForm(payload, request.FILES, instance=loan)
        if form.is_valid():
            updated_loan = form.save(commit=False)
            updated_loan.updated_by = request.user
            updated_loan.save()

            # Keep group association unchanged for this edit flow.
            if group_loan.group_id != form.cleaned_data['group'].id:
                group_loan.group = form.cleaned_data['group']
                group_loan.save(update_fields=['group'])

            messages.success(request, f'Group loan {updated_loan.loan_number} updated successfully.')
            return redirect('loans:group_loans')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ComprehensiveGroupLoanForm(instance=loan, initial={'group': group_loan.group})

    context = {
        'form': form,
        'group_loan': group_loan,
        'loan': loan,
        'title': f'Edit Group Loan {loan.loan_number}',
        'page_title': 'Edit Group Loan',
    }
    return render(request, 'loans/edit_group_loan.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def delete_group_loan(request, group_loan_id):
    """Soft-delete a group loan by rejecting it before disbursement."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    group_loan = get_object_or_404(GroupLoan.objects.select_related('loan', 'group'), id=group_loan_id)
    loan = group_loan.loan

    if loan.status not in {LoanStatusChoices.PENDING, LoanStatusChoices.APPROVED}:
        messages.error(request, 'Only pending or approved group loans can be deleted.')
        return redirect('loans:group_loans')

    if request.method == 'POST':
        reason = request.POST.get('deletion_reason', '').strip() or 'Deleted by admin/manager'
        loan.status = LoanStatusChoices.REJECTED
        loan.rejection_reason = reason
        loan.rejected_by = request.user
        loan.rejection_date = timezone.now().date()
        loan.updated_by = request.user
        loan.save(update_fields=['status', 'rejection_reason', 'rejected_by', 'rejection_date', 'updated_by', 'updated_at'])

        messages.success(request, f'Group loan {loan.loan_number} deleted successfully.')
        return redirect('loans:group_loans')

    return render(request, 'loans/delete_group_loan.html', {'group_loan': group_loan, 'loan': loan})


@login_required
def borrowers_api(request):
    """API endpoint to fetch borrowers for autocomplete."""
    from apps.borrowers.models import Borrower
    
    borrowers = Borrower.objects.filter(status=BorrowerStatus.ACTIVE).values(
        'id', 'borrower_id', 'first_name', 'last_name', 'phone_number'
    )
    
    borrowers_list = list(borrowers)
    return JsonResponse(borrowers_list, safe=False)


@login_required
def borrower_search_api(request):
    """API endpoint to search all registered borrowers."""
    import logging
    logger = logging.getLogger(__name__)
    query = request.GET.get('q', '').strip()
    has_loans = request.GET.get('has_loans', 'true').lower() == 'true'
    
    try:
        borrowers = Borrower.objects.all()
        
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
        
    except ValueError as e:
        logger.warning(f'Invalid query parameter in borrower_search_api: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': 'Invalid search parameters',
            'error_type': 'invalid_input'
        })
    except Exception as e:
        logger.error(f'Error in borrower_search_api: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': 'Search failed',
            'error_type': 'server_error'
        })


@login_required
def borrowers_with_loans_api(request):
    """API endpoint to fetch all borrowers with active loans."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from apps.borrowers.models import BorrowerStatus
        from apps.core.models import LoanStatusChoices
        
        borrowers = Borrower.objects.filter(
            status=BorrowerStatus.ACTIVE,
            loans__isnull=False,
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
        
    except ImportError as e:
        logger.error(f'Import error in borrowers_with_loans_api: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': 'Service unavailable',
            'error_type': 'service_error'
        })
    except Exception as e:
        logger.error(f'Error in borrowers_with_loans_api: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': 'Failed to fetch borrowers',
            'error_type': 'server_error'
        })


@login_required
def borrower_loans_api(request, borrower_id):
    """API endpoint to fetch active loans for a specific borrower."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from apps.borrowers.models import BorrowerStatus
        from apps.core.models import LoanStatusChoices
        
        borrower = get_object_or_404(Borrower, id=borrower_id, status=BorrowerStatus.ACTIVE)
        
        # Return all loans associated with this borrower.
        loans = Loan.objects.filter(
            borrower=borrower,
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
        
    except ImportError as e:
        logger.error(f'Import error in borrower_loans_api: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': 'Service unavailable',
            'error_type': 'service_error'
        })
    except Exception as e:
        logger.error(f'Error fetching loans for borrower {borrower_id}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': 'Failed to fetch borrower loans',
            'error_type': 'server_error'
        })


