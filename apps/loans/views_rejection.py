"""
Views for loan rejection and reversal workflows.
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_http_methods
from .models import Loan, LoanStatusChoices
from .forms_rejection import (
    LoanRejectionForm, LoanRejectionReversalForm, RejectedLoanEditForm
)

logger = logging.getLogger(__name__)


@login_required
@permission_required('loans.can_reject_loan', raise_exception=True)
@require_http_methods(["GET", "POST"])
def reject_loan(request, loan_id):
    """Reject a pending loan application."""
    # Allow rejecting both PENDING and PENDING (reversed) loans
    loan = get_object_or_404(Loan, id=loan_id, status=LoanStatusChoices.PENDING)
    
    if request.method == 'POST':
        form = LoanRejectionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                loan.status = LoanStatusChoices.REJECTED
                loan.rejected_by = request.user
                loan.rejection_date = timezone.now().date()
                loan.rejection_reason = form.cleaned_data['rejection_reason']
                # Clear reversal flag if this is a re-rejection
                loan.is_rejection_reversed = False
                loan.reversed_rejection_date = None
                loan.rejection_reversed_by = None
                loan.reversal_reason = None
                loan.save()
                
                # Log the action
                logger.info(
                    f'Loan {loan.loan_number} rejected by {request.user.username}. '
                    f'Reason: {loan.rejection_reason[:100]}'
                )
            
            messages.success(
                request,
                f'Loan {loan.loan_number} has been rejected.'
            )
            return redirect('loans:loan_detail', loan_id=loan.id)
    else:
        form = LoanRejectionForm()
    
    context = {
        'form': form,
        'loan': loan,
        'title': f'Reject Loan {loan.loan_number}',
        'action': 'Reject'
    }
    return render(request, 'loans/reject_loan.html', context)


@login_required
@permission_required('loans.can_reverse_rejection', raise_exception=True)
@require_http_methods(["GET", "POST"])
def reverse_loan_rejection(request, loan_id):
    """Reverse a rejected loan (admin only)."""
    loan = get_object_or_404(Loan, id=loan_id, status=LoanStatusChoices.REJECTED)
    
    if request.method == 'POST':
        form = LoanRejectionReversalForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Store original rejection info for history
                original_rejection_reason = loan.rejection_reason
                
                # Reverse the rejection - ALWAYS return to PENDING status
                loan.is_rejection_reversed = True
                loan.reversed_rejection_date = timezone.now().date()
                loan.rejection_reversed_by = request.user
                loan.reversal_reason = form.cleaned_data['reversal_reason']
                loan.status = LoanStatusChoices.PENDING  # Always set to PENDING
                loan.rejected_by = None
                loan.rejection_date = None
                
                loan.save()
                
                # Log the action with complete history
                logger.info(
                    f'Loan {loan.loan_number} rejection reversed by {request.user.username}. '
                    f'Original reason: {original_rejection_reason[:100]}. '
                    f'Reversal reason: {loan.reversal_reason[:100]}'
                )
            
            messages.success(
                request,
                f'Loan {loan.loan_number} rejection has been reversed.'
            )
            
            messages.info(
                request,
                f'Loan is now in PENDING status. Borrower can edit details and resubmit.'
            )
            return redirect('loans:edit_rejected_loan', loan_id=loan.id)
    else:
        form = LoanRejectionReversalForm()
    
    context = {
        'form': form,
        'loan': loan,
        'original_reason': loan.rejection_reason,
        'rejected_by': loan.rejected_by.get_full_name() if loan.rejected_by else '—',
        'rejection_date': loan.rejection_date,
        'title': f'Reverse Rejection - Loan {loan.loan_number}',
        'action': 'Reverse Rejection'
    }
    return render(request, 'loans/reverse_loan_rejection.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_reversed_loan(request, loan_id):
    """Edit a reversed-rejection loan before resubmission."""
    loan = get_object_or_404(
        Loan, 
        id=loan_id,
        status=LoanStatusChoices.PENDING,
        is_rejection_reversed=True
    )
    
    # Only admin can edit or borrower (who registered)
    is_admin = request.user.is_staff or request.user.is_superuser
    is_borrower_officer = loan.borrower.registered_by == request.user if loan.borrower else False
    
    if not (is_admin or is_borrower_officer):
        messages.error(request, 'You do not have permission to edit this loan.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    if request.method == 'POST':
        form = RejectedLoanEditForm(request.POST, instance=loan)
        if form.is_valid():
            with transaction.atomic():
                loan = form.save()
                
                logger.info(
                    f'Loan {loan.loan_number} edited after rejection reversal by {request.user.username}'
                )
            
            messages.success(
                request,
                f'Loan {loan.loan_number} has been updated. You can now resubmit it.'
            )
            return redirect('loans:loan_detail', loan_id=loan.id)
    else:
        form = RejectedLoanEditForm(instance=loan)
    
    context = {
        'form': form,
        'loan': loan,
        'title': f'Edit Loan {loan.loan_number}',
        'is_reversed': True,
        'original_rejection': loan.rejection_reason
    }
    return render(request, 'loans/edit_reversed_loan.html', context)


@login_required
@require_http_methods(["POST"])
def resubmit_reversed_loan(request, loan_id):
    """Resubmit a reversed-rejection loan for approval."""
    loan = get_object_or_404(
        Loan,
        id=loan_id,
        status=LoanStatusChoices.PENDING,
        is_rejection_reversed=True
    )
    
    # Only borrower or admin can resubmit
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if not is_admin:
        messages.error(request, 'Only admin can resubmit loans.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    with transaction.atomic():
        # Note: Status stays PENDING, just reset reversal flag if desired
        loan.is_rejection_reversed = False  # Clear the reversal flag
        loan.save(update_fields=['is_rejection_reversed'])
        
        logger.info(
            f'Loan {loan.loan_number} resubmitted by {request.user.username} after rejection reversal'
        )
    
    messages.success(
        request,
        f'Loan {loan.loan_number} has been resubmitted for approval.'
    )
    return redirect('loans:loan_detail', loan_id=loan.id)


@login_required
def rejected_loans_list(request):
    """View list of rejected loans."""
    rejected_loans = Loan.objects.filter(
        status=LoanStatusChoices.REJECTED
    ).select_related('borrower', 'rejected_by', 'rejection_reversed_by').order_by('-rejection_date')
    
    # Separate reversed and non-reversed
    reversed_loans = rejected_loans.filter(is_rejection_reversed=True)
    current_rejected = rejected_loans.filter(is_rejection_reversed=False)
    
    # Calculate reversal rate
    total_rejections = reversed_loans.count() + current_rejected.count()
    reversal_rate = 0
    if total_rejections > 0:
        reversal_rate = round((reversed_loans.count() / total_rejections) * 100, 1)
    
    context = {
        'reversed_loans': reversed_loans,
        'current_rejected': current_rejected,
        'reversal_rate': reversal_rate,
        'total_rejections': total_rejections,
        'title': 'Rejected Loans Management'
    }
    return render(request, 'loans/rejected_loans_list.html', context)
