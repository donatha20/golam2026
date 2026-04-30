"""
Views for savings management system.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q, Count, Avg, Min, Max
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    SavingsCategory, SavingsCharge, SavingsProduct, SavingsLoanRule, 
    SavingsAccount, SavingsTransaction, SavingsInterestCalculation, 
    SavingsAccountHold
)
from apps.accounts.models import UserActivity, UserRole
from apps.borrowers.models import Borrower


def _require_admin_access(request):
    """Restrict sensitive actions to admin/manager-level users."""
    if any([
        getattr(request.user, 'role', None) in {UserRole.ADMIN, UserRole.MANAGER},
        getattr(request.user, 'is_admin', False),
        getattr(request.user, 'is_staff', False),
        getattr(request.user, 'is_superuser', False),
    ]):
        return None

    messages.error(request, 'Access denied. Admin or manager privileges required.')
    return redirect('core:dashboard')


@login_required
def dashboard(request):
    """Savings management dashboard."""
    # Account statistics
    total_accounts = SavingsAccount.objects.count()
    total_balance = SavingsAccount.objects.aggregate(
        total=Sum('balance')
    )['total'] or Decimal('0.00')

    account_stats = {
        'total_accounts': total_accounts,
        'active_accounts': SavingsAccount.objects.filter(
            status='active'
        ).count(),
        'total_balance': total_balance,
        'average_balance': total_balance / total_accounts if total_accounts > 0 else Decimal('0.00'),
        'dormant_accounts': SavingsAccount.objects.filter(
            is_dormant=True
        ).count(),
    }
    
    # Transaction statistics
    today = timezone.now().date()
    transaction_stats = {
        'today_deposits': SavingsTransaction.objects.filter(
            transaction_date=today,
            transaction_type='deposit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'today_withdrawals': SavingsTransaction.objects.filter(
            transaction_date=today,
            transaction_type='withdrawal'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'pending_transactions': SavingsTransaction.objects.filter(
            status='pending'
        ).count(),
    }
    
    # Interest statistics
    interest_stats = {
        'total_interest_accrued': SavingsAccount.objects.aggregate(
            total=Sum('accrued_interest')
        )['total'] or Decimal('0.00'),
        'total_interest_earned': SavingsAccount.objects.aggregate(
            total=Sum('total_interest_earned')
        )['total'] or Decimal('0.00'),
        'pending_interest_calculations': SavingsInterestCalculation.objects.filter(
            is_posted=False
        ).count(),
    }
    
    # Recent activities
    recent_accounts = SavingsAccount.objects.select_related(
        'borrower', 'savings_product'
    ).order_by('-created_at')[:5]
    
    recent_transactions = SavingsTransaction.objects.select_related(
        'savings_account__borrower'
    ).order_by('-created_at')[:10]
    
    # Accounts by product
    accounts_by_product = SavingsProduct.objects.annotate(
        account_count=Count('accounts'),
        total_balance=Sum('accounts__balance')
    ).filter(account_count__gt=0)
    
    context = {
        'account_stats': account_stats,
        'transaction_stats': transaction_stats,
        'interest_stats': interest_stats,
        'recent_accounts': recent_accounts,
        'recent_transactions': recent_transactions,
        'accounts_by_product': accounts_by_product,
        'title': 'Savings Management Dashboard',
        'page_title': 'Savings Management',
    }
    
    return render(request, 'savings/dashboard.html', context)


# ==============================================================================
# VIEW CATEGORIES SECTION
# ==============================================================================

@login_required
def view_categories(request):
    """View all savings product categories."""
    categories = SavingsCategory.objects.annotate(
        product_count=Count('products')
    ).order_by('display_order', 'name')
    
    context = {
        'categories': categories,
        'title': 'View Categories',
        'page_title': 'Savings Categories',
    }
    
    return render(request, 'savings/view_categories.html', context)


@login_required
def create_categories(request):
    """Create new savings product category."""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        code = request.POST.get('code')
        display_order = request.POST.get('display_order', 0)
        
        try:
            category = SavingsCategory.objects.create(
                name=name,
                description=description,
                code=code,
                display_order=int(display_order),
                created_by=request.user
            )
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('savings:view_categories')
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
    
    context = {
        'title': 'Create Category',
        'page_title': 'New Category',
    }
    
    return render(request, 'savings/create_categories.html', context)


@login_required
def edit_category(request, category_id):
    """Edit existing category."""
    category = get_object_or_404(SavingsCategory, id=category_id)
    
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.code = request.POST.get('code')
        category.display_order = int(request.POST.get('display_order', 0))
        category.is_active = request.POST.get('is_active') == 'on'
        
        try:
            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('savings:view_categories')
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
    
    context = {
        'category': category,
        'title': 'Edit Category',
        'page_title': f'Edit {category.name}',
    }
    
    return render(request, 'savings/edit_category.html', context)


@login_required
def delete_category(request, category_id):
    """Delete category."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    category = get_object_or_404(SavingsCategory, id=category_id)
    
    if request.method == 'POST':
        try:
            category_name = category.name
            category.delete()
            messages.success(request, f'Category "{category_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}')
    
    return redirect('savings:view_categories')


# ==============================================================================
# CHARGES MANAGEMENT SECTION
# ==============================================================================

@login_required
def set_charges(request):
    """
    Universal charge setting view that handles both withdraw and service charges.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    charge_types = [
        ('withdrawal', 'Withdrawal Charges'),
        ('service', 'Service Charges'),
        ('maintenance', 'Maintenance Charges'),
    ]
    
    calculation_methods = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('tiered', 'Tiered'),
    ]
    
    if request.method == 'POST':
        name = request.POST.get('name')
        charge_type = request.POST.get('charge_type')
        calculation_method = request.POST.get('calculation_method')
        fixed_amount = request.POST.get('fixed_amount')
        percentage_rate = request.POST.get('percentage_rate')
        minimum_amount = request.POST.get('minimum_amount')
        maximum_amount = request.POST.get('maximum_amount')
        description = request.POST.get('description', '')
        
        try:
            # Create new charge
            charge = SavingsCharge.objects.create(
                name=name,
                charge_type=charge_type,
                calculation_method=calculation_method,
                fixed_amount=Decimal(fixed_amount) if fixed_amount else None,
                percentage_rate=Decimal(percentage_rate) if percentage_rate else None,
                minimum_amount=Decimal(minimum_amount) if minimum_amount else None,
                maximum_amount=Decimal(maximum_amount) if maximum_amount else None,
                description=description,
                is_active=True,
                created_by=request.user
            )
            
            messages.success(request, f'Charge "{name}" created successfully.')
            return redirect('savings:view_charges')
            
        except Exception as e:
            messages.error(request, f'Error creating charge: {str(e)}')
    
    context = {
        'charge_types': charge_types,
        'calculation_methods': calculation_methods,
    }
    
    return render(request, 'savings/set_charges.html', context)


@login_required
def set_withdraw_charges(request):
    """Set withdrawal charges configuration."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        calculation_method = request.POST.get('calculation_method')
        fixed_amount = request.POST.get('fixed_amount', '0.00')
        percentage_rate = request.POST.get('percentage_rate', '0.00')
        minimum_amount = request.POST.get('minimum_amount', '0.00')
        maximum_amount = request.POST.get('maximum_amount') or None
        
        try:
            charge = SavingsCharge.objects.create(
                name=name,
                description=description,
                charge_type='withdrawal',
                calculation_method=calculation_method,
                fixed_amount=Decimal(fixed_amount),
                percentage_rate=Decimal(percentage_rate),
                minimum_amount=Decimal(minimum_amount),
                maximum_amount=Decimal(maximum_amount) if maximum_amount else None,
                created_by=request.user
            )
            messages.success(request, f'Withdrawal charge "{charge.name}" created successfully.')
            return redirect('savings:view_withdraw_charges')
        except Exception as e:
            messages.error(request, f'Error creating withdrawal charge: {str(e)}')
    
    context = {
        'title': 'Set Withdraw Charges',
        'page_title': 'Configure Withdrawal Charges',
        'charge_type': 'withdrawal',
    }
    
    return render(request, 'savings/set_charges.html', context)


@login_required
def set_service_charges(request):
    """Set service charges configuration."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        calculation_method = request.POST.get('calculation_method')
        fixed_amount = request.POST.get('fixed_amount', '0.00')
        percentage_rate = request.POST.get('percentage_rate', '0.00')
        minimum_amount = request.POST.get('minimum_amount', '0.00')
        maximum_amount = request.POST.get('maximum_amount') or None
        frequency = request.POST.get('frequency', 'per_transaction')
        
        try:
            charge = SavingsCharge.objects.create(
                name=name,
                description=description,
                charge_type='service',
                calculation_method=calculation_method,
                fixed_amount=Decimal(fixed_amount),
                percentage_rate=Decimal(percentage_rate),
                minimum_amount=Decimal(minimum_amount),
                maximum_amount=Decimal(maximum_amount) if maximum_amount else None,
                frequency=frequency,
                created_by=request.user
            )
            messages.success(request, f'Service charge "{charge.name}" created successfully.')
            return redirect('savings:view_service_charges')
        except Exception as e:
            messages.error(request, f'Error creating service charge: {str(e)}')
    
    context = {
        'title': 'Set Service Charges',
        'page_title': 'Configure Service Charges',
        'charge_type': 'service',
    }
    
    return render(request, 'savings/set_charges.html', context)


@login_required
def view_charges(request):
    """
    View all charges with filtering capabilities.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    charges = SavingsCharge.objects.all()
    
    # Apply filters
    charge_type = request.GET.get('charge_type')
    method = request.GET.get('method')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if charge_type:
        charges = charges.filter(charge_type=charge_type)
    
    if method:
        charges = charges.filter(calculation_method=method)
    
    if status:
        is_active = status == 'active'
        charges = charges.filter(is_active=is_active)
    
    if search:
        charges = charges.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Handle POST actions (activate, deactivate, delete)
    if request.method == 'POST':
        denied_response = _require_admin_access(request)
        if denied_response:
            return denied_response

        action = request.POST.get('action')
        charge_id = request.POST.get('charge_id')
        
        try:
            charge = SavingsCharge.objects.get(id=charge_id)
            
            if action == 'activate':
                charge.is_active = True
                charge.save()
                messages.success(request, f'Charge "{charge.name}" activated.')
            elif action == 'deactivate':
                charge.is_active = False
                charge.save()
                messages.success(request, f'Charge "{charge.name}" deactivated.')
            elif action == 'delete':
                charge_name = charge.name
                charge.delete()
                messages.success(request, f'Charge "{charge_name}" deleted.')
            
        except SavingsCharge.DoesNotExist:
            messages.error(request, 'Charge not found.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('savings:view_charges')
    
    # Calculate summary statistics
    total_charges = charges.count()
    active_charges = charges.filter(is_active=True).count()
    inactive_charges = charges.filter(is_active=False).count()
    fixed_charges = charges.filter(calculation_method='fixed').count()
    percentage_charges = charges.filter(calculation_method='percentage').count()
    
    context = {
        'charges': charges,
        'total_charges': total_charges,
        'active_charges': active_charges,
        'inactive_charges': inactive_charges,
        'fixed_charges': fixed_charges,
        'percentage_charges': percentage_charges,
    }
    
    return render(request, 'savings/view_charges.html', context)


@login_required
def view_withdraw_charges(request):
    """View all withdrawal charges."""
    charges = SavingsCharge.objects.filter(
        charge_type='withdrawal'
    ).order_by('-created_at')
    
    context = {
        'charges': charges,
        'charge_type': 'withdrawal',
        'title': 'View Withdraw Charges',
        'page_title': 'Withdrawal Charges',
    }
    
    return render(request, 'savings/view_charges.html', context)


@login_required
def view_service_charges(request):
    """View all service charges."""
    charges = SavingsCharge.objects.filter(
        charge_type='service'
    ).order_by('-created_at')
    
    context = {
        'charges': charges,
        'charge_type': 'service',
        'title': 'View Service Charges',
        'page_title': 'Service Charges',
    }
    
    return render(request, 'savings/view_charges.html', context)


@login_required
def edit_charge(request, charge_id):
    """Edit existing charge."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    charge = get_object_or_404(SavingsCharge, id=charge_id)
    
    if request.method == 'POST':
        charge.name = request.POST.get('name')
        charge.description = request.POST.get('description')
        charge.calculation_method = request.POST.get('calculation_method')
        charge.fixed_amount = Decimal(request.POST.get('fixed_amount', '0.00'))
        charge.percentage_rate = Decimal(request.POST.get('percentage_rate', '0.00'))
        charge.minimum_amount = Decimal(request.POST.get('minimum_amount', '0.00'))
        maximum_amount = request.POST.get('maximum_amount')
        charge.maximum_amount = Decimal(maximum_amount) if maximum_amount else None
        charge.frequency = request.POST.get('frequency', 'per_transaction')
        charge.is_active = request.POST.get('is_active') == 'on'
        
        try:
            charge.save()
            messages.success(request, f'Charge "{charge.name}" updated successfully.')
            if charge.charge_type == 'withdrawal':
                return redirect('savings:view_withdraw_charges')
            else:
                return redirect('savings:view_service_charges')
        except Exception as e:
            messages.error(request, f'Error updating charge: {str(e)}')
    
    context = {
        'charge': charge,
        'title': 'Edit Charge',
        'page_title': f'Edit {charge.name}',
    }
    
    return render(request, 'savings/edit_charge.html', context)


@login_required
def delete_charge(request, charge_id):
    """Delete charge."""
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response

    charge = get_object_or_404(SavingsCharge, id=charge_id)
    charge_type = charge.charge_type
    
    if request.method == 'POST':
        try:
            charge_name = charge.name
            charge.delete()
            messages.success(request, f'Charge "{charge_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting charge: {str(e)}')
    
    if charge_type == 'withdrawal':
        return redirect('savings:view_withdraw_charges')
    else:
        return redirect('savings:view_service_charges')


# ==============================================================================
# ACCOUNT MANAGEMENT SECTION
# ==============================================================================

@login_required
def account_list(request):
    """
    Display list of all savings accounts.
    This is an alias for view_accounts to maintain backward compatibility.
    """
    return view_accounts(request)


@login_required
def view_accounts(request):
    """View all savings accounts with filtering and search."""
    accounts = SavingsAccount.objects.select_related(
        'borrower', 'savings_product', 'opened_by'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        accounts = accounts.filter(
            Q(account_number__icontains=search_query) |
            Q(borrower__first_name__icontains=search_query) |
            Q(borrower__last_name__icontains=search_query) |
            Q(borrower__phone_number__icontains=search_query)
        )
    
    # Filter by product
    product_id = request.GET.get('product', '')
    if product_id:
        accounts = accounts.filter(savings_product_id=product_id)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    # Filter by balance range
    min_balance = request.GET.get('min_balance', '')
    max_balance = request.GET.get('max_balance', '')
    if min_balance:
        accounts = accounts.filter(balance__gte=Decimal(min_balance))
    if max_balance:
        accounts = accounts.filter(balance__lte=Decimal(max_balance))
    
    # Pagination
    paginator = Paginator(accounts, 25)
    page_number = request.GET.get('page')
    accounts = paginator.get_page(page_number)
    
    # Get filter options
    products = SavingsProduct.objects.filter(is_active=True)
    
    context = {
        'accounts': accounts,
        'products': products,
        'search_query': search_query,
        'product_id': product_id,
        'status_filter': status_filter,
        'min_balance': min_balance,
        'max_balance': max_balance,
        'account_statuses': SavingsAccount._meta.get_field('status').choices,
        'title': 'View Accounts',
        'page_title': 'Savings Accounts',
    }
    
    return render(request, 'savings/view_accounts.html', context)


@login_required
def record_transaction(request, transaction_type):
    """
    Universal transaction recording view that handles deposit, withdrawal, charges, and interest.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    # Validate transaction type
    valid_types = ['deposit', 'withdrawal', 'charges', 'interest']
    if transaction_type not in valid_types:
        messages.error(request, 'Invalid transaction type.')
        return redirect('savings:dashboard')
    
    # Get all active savings accounts for the form
    accounts = SavingsAccount.objects.filter(status='active').select_related('borrower', 'savings_product')
    
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        amount = request.POST.get('amount')
        notes = request.POST.get('notes', '')
        
        try:
            # Validate input
            if not account_id or not amount:
                messages.error(request, 'Account and amount are required.')
                return render(request, 'savings/record_transaction.html', {
                    'accounts': accounts,
                    'transaction_type': transaction_type
                })
            
            account = SavingsAccount.objects.get(id=account_id)
            amount = Decimal(amount)
            
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero.')
                return render(request, 'savings/record_transaction.html', {
                    'accounts': accounts,
                    'transaction_type': transaction_type
                })
            
            model_transaction_type = 'charge' if transaction_type == 'charges' else transaction_type

            balance_before = account.balance
            balance_after = balance_before

            if transaction_type == 'deposit':
                balance_after = balance_before + amount
            elif transaction_type == 'withdrawal':
                if account.available_balance < amount:
                    messages.error(request, 'Insufficient balance for withdrawal.')
                    return render(request, 'savings/record_transaction.html', {
                        'accounts': accounts,
                        'transaction_type': transaction_type
                    })
                balance_after = balance_before - amount
            elif transaction_type == 'charges':
                if account.available_balance < amount:
                    messages.error(request, 'Insufficient balance for charges.')
                    return render(request, 'savings/record_transaction.html', {
                        'accounts': accounts,
                        'transaction_type': transaction_type
                    })
                balance_after = balance_before - amount
            elif transaction_type == 'interest':
                balance_after = balance_before + amount

            SavingsTransaction.objects.create(
                savings_account=account,
                transaction_type=model_transaction_type,
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                processed_by=request.user,
                notes=notes,
                status='completed'
            )

            account.balance = balance_after
            account.available_balance = account.balance - account.total_holds
            account.last_transaction_date = timezone.now().date()
            account.save()
            
            messages.success(request, f'{transaction_type.title()} of Tsh {amount:,.2f} recorded successfully.')
            return redirect('savings:view_accounts')
            
        except SavingsAccount.DoesNotExist:
            messages.error(request, 'Selected account not found.')
        except (ValueError, InvalidOperation):
            messages.error(request, 'Invalid amount entered.')
        except Exception as e:
            messages.error(request, f'Error recording transaction: {str(e)}')
    
    context = {
        'accounts': accounts,
        'transaction_type': transaction_type,
    }
    
    return render(request, 'savings/record_transaction.html', context)


def transaction_list(request):
    """
    Display list of all transactions with filtering capabilities.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    transactions = SavingsTransaction.objects.all().select_related('account', 'account__borrower').order_by('-transaction_date')
    
    context = {
        'transactions': transactions,
    }
    
    return render(request, 'savings/transaction_list.html', context)


def process_transaction(request):
    """
    Process a new savings transaction.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    accounts = SavingsAccount.objects.filter(status='active').select_related('borrower', 'product')
    
    context = {
        'accounts': accounts,
    }
    
    return render(request, 'savings/process_transaction.html', context)


@login_required
def transaction_detail(request, transaction_id):
    """
    Display detailed view of a specific transaction.
    """
    transaction = get_object_or_404(
        SavingsTransaction.objects.select_related('savings_account__borrower', 'processed_by'),
        id=transaction_id
    )
    
    context = {
        'transaction': transaction,
    }
    
    return render(request, 'savings/transaction_detail.html', context)


@login_required
@require_http_methods(["POST"])
def reverse_transaction(request, transaction_id):
    """
    Reverse a specific transaction.
    """
    denied_response = _require_admin_access(request)
    if denied_response:
        return denied_response
    
    transaction = get_object_or_404(SavingsTransaction, id=transaction_id)
    account = transaction.savings_account

    if not account:
        messages.error(request, 'Cannot reverse transaction without an associated savings account.')
        return redirect('savings:transaction_detail', transaction_id=transaction_id)

    if transaction.status != 'completed':
        messages.error(request, 'Only completed transactions can be reversed.')
        return redirect('savings:transaction_detail', transaction_id=transaction_id)
    
    try:
        # Reverse by applying the opposite financial effect to account balance.
        if transaction.transaction_type in ['deposit', 'interest']:
            if account.balance < transaction.amount:
                messages.error(request, 'Cannot reverse: current account balance is below transaction amount.')
                return redirect('savings:transaction_detail', transaction_id=transaction_id)
            reverse_type = 'withdrawal'
            balance_before = account.balance
            balance_after = account.balance - transaction.amount
        else:
            reverse_type = 'deposit'
            balance_before = account.balance
            balance_after = account.balance + transaction.amount

        SavingsTransaction.objects.create(
            savings_account=account,
            transaction_type=reverse_type,
            amount=transaction.amount,
            balance_before=balance_before,
            balance_after=balance_after,
            processed_by=request.user,
            notes=f'Reversal of transaction {transaction.reference_number or transaction.id}',
            status='completed'
        )

        account.balance = balance_after
        account.available_balance = account.balance - account.total_holds
        account.last_transaction_date = timezone.now().date()
        account.save()

        transaction.status = 'cancelled'
        transaction.save(update_fields=['status'])

        messages.success(request, 'Transaction reversed successfully.')
        return redirect('savings:transaction_list')

    except Exception as e:
        messages.error(request, f'Error reversing transaction: {str(e)}')
    
    return redirect('savings:transaction_detail', transaction_id=transaction_id)


def interest_calculation(request):
    """
    Interest calculation and management.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    calculations = SavingsInterestCalculation.objects.all().select_related('account', 'account__borrower').order_by('-calculation_date')
    
    context = {
        'calculations': calculations,
    }
    
    return render(request, 'savings/interest_calculation.html', context)


def reports(request):
    """
    Savings reports dashboard.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    context = {
        'title': 'Savings Reports',
    }
    
    return render(request, 'savings/reports.html', context)


def record_deposited(request):
    """Record new deposit transaction."""
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        amount = request.POST.get('amount')
        notes = request.POST.get('notes', '')
        
        try:
            account = get_object_or_404(SavingsAccount, id=account_id)
            amount = Decimal(amount)
            
            can_deposit, message = account.can_deposit(amount)
            if not can_deposit:
                messages.error(request, message)
                return redirect('savings:record_deposited')
            
            # Create deposit transaction
            transaction_obj = SavingsTransaction.objects.create(
                savings_account=account,
                transaction_type='deposit',
                amount=amount,
                balance_before=account.balance,
                balance_after=account.balance + amount,
                processed_by=request.user,
                notes=notes,
                status='completed'
            )
            
            # Update account balance
            account.balance += amount
            account.available_balance = account.balance - account.total_holds
            account.last_transaction_date = timezone.now().date()
            account.save()
            
            messages.success(request, f'Deposit of Tsh {amount} recorded successfully. Reference: {transaction_obj.reference_number}')
            return redirect('savings:view_deposited')
            
        except Exception as e:
            messages.error(request, f'Error recording deposit: {str(e)}')
    
    accounts = SavingsAccount.objects.filter(
        status='active'
    ).select_related('borrower').order_by('account_number')
    
    context = {
        'accounts': accounts,
        'transaction_type': 'deposit',
        'title': 'Record Deposited',
        'page_title': 'Record Deposit',
    }
    
    return render(request, 'savings/record_transaction.html', context)


@login_required
def record_withdrawn(request):
    """Record new withdrawal transaction."""
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        amount = request.POST.get('amount')
        notes = request.POST.get('notes', '')
        
        try:
            account = get_object_or_404(SavingsAccount, id=account_id)
            amount = Decimal(amount)
            
            can_withdraw, message = account.can_withdraw(amount)
            if not can_withdraw:
                messages.error(request, message)
                return redirect('savings:record_withdrawn')
            
            # Check for withdrawal charges
            withdrawal_charges = SavingsCharge.objects.filter(
                charge_type='withdrawal',
                is_active=True
            )
            
            total_charges = Decimal('0.00')
            charge_transactions = []
            
            for charge in withdrawal_charges:
                if charge.applies_to_all_products or account.savings_product in charge.applicable_products.all():
                    charge_amount = charge.calculate_charge(amount)
                    if charge_amount > 0:
                        total_charges += charge_amount
                        charge_transactions.append((charge, charge_amount))
            
            # Check if account has sufficient balance including charges
            total_deduction = amount + total_charges
            if account.balance < total_deduction:
                messages.error(request, f'Insufficient balance. Required: Tsh {total_deduction} (Amount: Tsh {amount} + Charges: Tsh {total_charges}), Available: Tsh {account.balance}')
                return redirect('savings:record_withdrawn')
            
            # Create withdrawal transaction
            transaction_obj = SavingsTransaction.objects.create(
                savings_account=account,
                transaction_type='withdrawal',
                amount=amount,
                balance_before=account.balance,
                balance_after=account.balance - total_deduction,
                processed_by=request.user,
                notes=notes,
                status='completed'
            )
            
            # Create charge transactions
            for charge, charge_amount in charge_transactions:
                SavingsTransaction.objects.create(
                    savings_account=account,
                    transaction_type='charge',
                    amount=charge_amount,
                    balance_before=account.balance - amount,
                    balance_after=account.balance - amount - charge_amount,
                    related_charge=charge,
                    charge_description=f'Withdrawal charge: {charge.name}',
                    processed_by=request.user,
                    status='completed'
                )
            
            # Update account balance
            account.balance -= total_deduction
            account.available_balance = account.balance - account.total_holds
            account.last_transaction_date = timezone.now().date()
            account.save()
            
            message = f'Withdrawal of Tsh {amount} recorded successfully. Reference: {transaction_obj.reference_number}'
            if total_charges > 0:
                message += f' (Charges applied: Tsh {total_charges})'
            messages.success(request, message)
            return redirect('savings:view_withdrawn')
            
        except Exception as e:
            messages.error(request, f'Error recording withdrawal: {str(e)}')
    
    accounts = SavingsAccount.objects.filter(
        status='active'
    ).select_related('borrower').order_by('account_number')
    
    context = {
        'accounts': accounts,
        'transaction_type': 'withdrawal',
        'title': 'Record Withdrawn',
        'page_title': 'Record Withdrawal',
    }
    
    return render(request, 'savings/record_transaction.html', context)


@login_required
def record_charges(request):
    """Record charges transaction."""
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        charge_id = request.POST.get('charge_id')
        custom_amount = request.POST.get('custom_amount')
        notes = request.POST.get('notes', '')
        
        try:
            account = get_object_or_404(SavingsAccount, id=account_id)
            charge = get_object_or_404(SavingsCharge, id=charge_id)
            
            if custom_amount:
                amount = Decimal(custom_amount)
            else:
                # Calculate charge based on current balance or fixed amount
                amount = charge.calculate_charge(account.balance)
            
            if amount <= 0:
                messages.error(request, 'Invalid charge amount.')
                return redirect('savings:record_charges')
            
            if account.balance < amount:
                messages.error(request, f'Insufficient balance. Required: Tsh {amount}, Available: Tsh {account.balance}')
                return redirect('savings:record_charges')
            
            # Create charge transaction
            transaction_obj = SavingsTransaction.objects.create(
                savings_account=account,
                transaction_type='charge',
                amount=amount,
                balance_before=account.balance,
                balance_after=account.balance - amount,
                related_charge=charge,
                charge_description=f'{charge.get_charge_type_display()}: {charge.name}',
                processed_by=request.user,
                notes=notes,
                status='completed'
            )
            
            # Update account balance
            account.balance -= amount
            account.available_balance = account.balance - account.total_holds
            account.last_transaction_date = timezone.now().date()
            account.save()
            
            messages.success(request, f'Charge of Tsh {amount} recorded successfully. Reference: {transaction_obj.reference_number}')
            return redirect('savings:view_charges')
            
        except Exception as e:
            messages.error(request, f'Error recording charge: {str(e)}')
    
    accounts = SavingsAccount.objects.filter(
        status='active'
    ).select_related('borrower').order_by('account_number')
    
    charges = SavingsCharge.objects.filter(is_active=True).order_by('charge_type', 'name')
    
    context = {
        'accounts': accounts,
        'charges': charges,
        'transaction_type': 'charge',
        'title': 'Record Charges',
        'page_title': 'Record Charges',
    }
    
    return render(request, 'savings/record_charges.html', context)


@login_required
def record_earned_interest(request):
    """Record earned interest transaction."""
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        amount = request.POST.get('amount')
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        notes = request.POST.get('notes', '')
        
        try:
            account = get_object_or_404(SavingsAccount, id=account_id)
            amount = Decimal(amount)
            
            if amount <= 0:
                messages.error(request, 'Interest amount must be positive.')
                return redirect('savings:record_earned_interest')
            
            # Create interest transaction
            transaction_obj = SavingsTransaction.objects.create(
                savings_account=account,
                transaction_type='interest',
                amount=amount,
                balance_before=account.balance,
                balance_after=account.balance + amount,
                processed_by=request.user,
                notes=f'Interest earned for period {period_start} to {period_end}. {notes}',
                status='completed'
            )
            
            # Update account balance and interest tracking
            account.balance += amount
            account.available_balance = account.balance - account.total_holds
            account.total_interest_earned += amount
            account.accrued_interest = Decimal('0.00')  # Reset accrued interest
            account.last_interest_posting = timezone.now().date()
            account.last_transaction_date = timezone.now().date()
            account.save()
            
            # Create interest calculation record
            if period_start and period_end:
                SavingsInterestCalculation.objects.create(
                    savings_account=account,
                    calculation_date=timezone.now().date(),
                    period_start_date=datetime.strptime(period_start, '%Y-%m-%d').date(),
                    period_end_date=datetime.strptime(period_end, '%Y-%m-%d').date(),
                    opening_balance=account.balance - amount,
                    closing_balance=account.balance,
                    average_balance=account.balance,  # Simplified
                    interest_rate=account.current_interest_rate,
                    days_in_period=(datetime.strptime(period_end, '%Y-%m-%d').date() - 
                                   datetime.strptime(period_start, '%Y-%m-%d').date()).days + 1,
                    interest_amount=amount,
                    is_posted=True,
                    posted_date=timezone.now().date(),
                    posted_by=request.user,
                    created_by=request.user
                )
            
            messages.success(request, f'Interest of Tsh {amount} recorded successfully. Reference: {transaction_obj.reference_number}')
            return redirect('savings:view_interests')
            
        except Exception as e:
            messages.error(request, f'Error recording interest: {str(e)}')
    
    accounts = SavingsAccount.objects.filter(
        status='active',
        balance__gt=0
    ).select_related('borrower', 'savings_product').order_by('account_number')
    
    context = {
        'accounts': accounts,
        'transaction_type': 'interest',
        'title': 'Record Earned Interest',
        'page_title': 'Record Interest',
    }
    
    return render(request, 'savings/record_interest.html', context)


# ==============================================================================
# TRANSACTION VIEWS SECTION
# ==============================================================================

@login_required
def view_deposited(request):
    """View all deposit transactions."""
    transactions = SavingsTransaction.objects.filter(
        transaction_type='deposit'
    ).select_related('savings_account__borrower', 'processed_by').order_by('-created_at')
    
    # Search and filter functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(savings_account__account_number__icontains=search_query) |
            Q(savings_account__borrower__first_name__icontains=search_query) |
            Q(savings_account__borrower__last_name__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Amount range filter
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    if min_amount:
        transactions = transactions.filter(amount__gte=Decimal(min_amount))
    if max_amount:
        transactions = transactions.filter(amount__lte=Decimal(max_amount))
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = SavingsTransaction.objects.filter(
        transaction_type='deposit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    today_amount = SavingsTransaction.objects.filter(
        transaction_type='deposit',
        transaction_date=timezone.now().date()
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'transactions': transactions,
        'transaction_type': 'deposit',
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'total_amount': total_amount,
        'today_amount': today_amount,
        'title': 'View Deposited',
        'page_title': 'Deposit Transactions',
    }
    
    return render(request, 'savings/view_transactions.html', context)


@login_required
def view_withdrawn(request):
    """View all withdrawal transactions."""
    transactions = SavingsTransaction.objects.filter(
        transaction_type='withdrawal'
    ).select_related('savings_account__borrower', 'processed_by').order_by('-created_at')
    
    # Search and filter functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(savings_account__account_number__icontains=search_query) |
            Q(savings_account__borrower__first_name__icontains=search_query) |
            Q(savings_account__borrower__last_name__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Amount range filter
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    if min_amount:
        transactions = transactions.filter(amount__gte=Decimal(min_amount))
    if max_amount:
        transactions = transactions.filter(amount__lte=Decimal(max_amount))
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = SavingsTransaction.objects.filter(
        transaction_type='withdrawal'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    today_amount = SavingsTransaction.objects.filter(
        transaction_type='withdrawal',
        transaction_date=timezone.now().date()
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'transactions': transactions,
        'transaction_type': 'withdrawal',
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'total_amount': total_amount,
        'today_amount': today_amount,
        'title': 'View Withdrawn',
        'page_title': 'Withdrawal Transactions',
    }
    
    return render(request, 'savings/view_transactions.html', context)


@login_required
def view_charges(request):
    """View all charge transactions."""
    transactions = SavingsTransaction.objects.filter(
        transaction_type__in=['charge', 'fee']
    ).select_related('savings_account__borrower', 'processed_by', 'related_charge').order_by('-created_at')
    
    # Search and filter functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(savings_account__account_number__icontains=search_query) |
            Q(savings_account__borrower__first_name__icontains=search_query) |
            Q(savings_account__borrower__last_name__icontains=search_query) |
            Q(charge_description__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Charge type filter
    charge_type = request.GET.get('charge_type', '')
    if charge_type:
        transactions = transactions.filter(related_charge__charge_type=charge_type)
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = SavingsTransaction.objects.filter(
        transaction_type__in=['charge', 'fee']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    today_amount = SavingsTransaction.objects.filter(
        transaction_type__in=['charge', 'fee'],
        transaction_date=timezone.now().date()
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Get charge types for filter
    charge_types = SavingsCharge.objects.values_list('charge_type', flat=True).distinct()
    
    context = {
        'transactions': transactions,
        'transaction_type': 'charge',
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'charge_type': charge_type,
        'charge_types': charge_types,
        'total_amount': total_amount,
        'today_amount': today_amount,
        'title': 'View Charges',
        'page_title': 'Charge Transactions',
    }
    
    return render(request, 'savings/view_transactions.html', context)


@login_required
def view_interests(request):
    """View all interest transactions."""
    transactions = SavingsTransaction.objects.filter(
        transaction_type='interest'
    ).select_related('savings_account__borrower', 'processed_by').order_by('-created_at')
    
    # Search and filter functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(savings_account__account_number__icontains=search_query) |
            Q(savings_account__borrower__first_name__icontains=search_query) |
            Q(savings_account__borrower__last_name__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = SavingsTransaction.objects.filter(
        transaction_type='interest'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    today_amount = SavingsTransaction.objects.filter(
        transaction_type='interest',
        transaction_date=timezone.now().date()
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Get interest calculations for additional context
    interest_calculations = SavingsInterestCalculation.objects.select_related(
        'savings_account__borrower'
    ).order_by('-calculation_date')[:10]
    
    context = {
        'transactions': transactions,
        'transaction_type': 'interest',
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_amount': total_amount,
        'today_amount': today_amount,
        'interest_calculations': interest_calculations,
        'title': 'View Interests',
        'page_title': 'Interest Transactions',
    }
    
    return render(request, 'savings/view_transactions.html', context)


@login_required
def view_balance(request):
    """View comprehensive account balances."""
    accounts = SavingsAccount.objects.select_related(
        'borrower', 'savings_product', 'opened_by'
    ).order_by('-balance')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        accounts = accounts.filter(
            Q(account_number__icontains=search_query) |
            Q(borrower__first_name__icontains=search_query) |
            Q(borrower__last_name__icontains=search_query) |
            Q(borrower__phone_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    # Filter by product
    product_id = request.GET.get('product', '')
    if product_id:
        accounts = accounts.filter(savings_product_id=product_id)
    
    # Filter by balance range
    min_balance = request.GET.get('min_balance', '')
    max_balance = request.GET.get('max_balance', '')
    if min_balance:
        accounts = accounts.filter(balance__gte=Decimal(min_balance))
    if max_balance:
        accounts = accounts.filter(balance__lte=Decimal(max_balance))
    
    # Filter by dormant status
    dormant_filter = request.GET.get('dormant', '')
    if dormant_filter == 'true':
        accounts = accounts.filter(is_dormant=True)
    elif dormant_filter == 'false':
        accounts = accounts.filter(is_dormant=False)
    
    # Pagination
    paginator = Paginator(accounts, 25)
    page_number = request.GET.get('page')
    accounts = paginator.get_page(page_number)
    
    # Calculate summary statistics
    summary_stats = {
        'total_accounts': SavingsAccount.objects.count(),
        'total_balance': SavingsAccount.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0.00'),
        'total_holds': SavingsAccount.objects.aggregate(total=Sum('total_holds'))['total'] or Decimal('0.00'),
        'available_balance': SavingsAccount.objects.aggregate(total=Sum('available_balance'))['total'] or Decimal('0.00'),
        'active_accounts': SavingsAccount.objects.filter(status='active').count(),
        'dormant_accounts': SavingsAccount.objects.filter(is_dormant=True).count(),
        'below_minimum': SavingsAccount.objects.extra(
            where=["balance < (SELECT minimum_balance FROM savings_savingsproduct WHERE id = savings_savingsaccount.savings_product_id)"]
        ).count() if SavingsAccount.objects.exists() else 0,
    }
    
    # Get filter options
    products = SavingsProduct.objects.filter(is_active=True)
    
    context = {
        'accounts': accounts,
        'products': products,
        'summary_stats': summary_stats,
        'search_query': search_query,
        'status_filter': status_filter,
        'product_id': product_id,
        'min_balance': min_balance,
        'max_balance': max_balance,
        'dormant_filter': dormant_filter,
        'account_statuses': SavingsAccount._meta.get_field('status').choices,
        'title': 'View Balance',
        'page_title': 'Account Balances',
    }
    
    return render(request, 'savings/view_balance.html', context)


@login_required
def account_detail(request, account_id):
    """View savings account details."""
    account = get_object_or_404(SavingsAccount, id=account_id)
    
    # Get recent transactions
    transactions = account.transactions.order_by('-created_at')[:20]
    
    # Get interest calculations
    interest_calculations = account.interest_calculations.order_by('-calculation_date')[:10]
    
    # Get active holds
    active_holds = account.holds.filter(status='active').order_by('-created_at')
    
    # Calculate statistics
    stats = {
        'total_deposits': account.transactions.filter(
            transaction_type='deposit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'total_withdrawals': account.transactions.filter(
            transaction_type='withdrawal'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'total_charges': account.transactions.filter(
            transaction_type__in=['charge', 'fee']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'total_interest': account.transactions.filter(
            transaction_type='interest'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'transaction_count': account.transactions.count(),
        'average_balance': account.transactions.aggregate(
            avg=Avg('balance_after')
        )['avg'] or Decimal('0.00'),
    }
    
    # Check loan eligibility for common loan categories
    loan_eligibility = {}
    common_loan_categories = ['personal', 'business', 'emergency', 'agricultural']
    for loan_category in common_loan_categories:
        is_eligible, message = account.check_loan_eligibility(loan_category, Decimal('10000'))
        loan_eligibility[loan_category] = {
            'eligible': is_eligible,
            'message': message
        }
    
    context = {
        'account': account,
        'transactions': transactions,
        'interest_calculations': interest_calculations,
        'active_holds': active_holds,
        'stats': stats,
        'loan_eligibility': loan_eligibility,
        'title': f'Account - {account.account_number}',
        'page_title': account.account_number,
    }
    
    return render(request, 'savings/account_detail.html', context)


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@login_required
def check_loan_eligibility_api(request):
    """API endpoint to check loan eligibility for a savings account."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            account_id = data.get('account_id')
            loan_category = data.get('loan_category')
            loan_amount = Decimal(str(data.get('loan_amount', '0')))

            account = get_object_or_404(SavingsAccount, id=account_id)
            is_eligible, message = account.check_loan_eligibility(loan_category, loan_amount)

            return JsonResponse({
                'eligible': is_eligible,
                'message': message,
                'account_balance': float(account.balance),
                'minimum_balance': float(account.minimum_balance_required)
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def account_balance_api(request, account_number):
    """API endpoint to get account balance."""
    try:
        account = get_object_or_404(SavingsAccount, account_number=account_number)

        return JsonResponse({
            'account_number': account.account_number,
            'balance': float(account.balance),
            'available_balance': float(account.available_balance),
            'minimum_balance': float(account.minimum_balance_required),
            'status': account.status,
            'borrower_name': account.borrower.get_full_name(),
            'product_name': account.savings_product.name if account.savings_product else 'N/A'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)
    """List all savings accounts with filtering and search."""
    accounts = SavingsAccount.objects.select_related(
        'borrower', 'savings_product', 'opened_by'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        accounts = accounts.filter(
            Q(account_number__icontains=search_query) |
            Q(borrower__first_name__icontains=search_query) |
            Q(borrower__last_name__icontains=search_query) |
            Q(borrower__phone_number__icontains=search_query)
        )
    
    # Filter by product
    product_id = request.GET.get('product', '')
    if product_id:
        accounts = accounts.filter(savings_product_id=product_id)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    # Filter by balance range
    min_balance = request.GET.get('min_balance', '')
    max_balance = request.GET.get('max_balance', '')
    if min_balance:
        accounts = accounts.filter(balance__gte=Decimal(min_balance))
    if max_balance:
        accounts = accounts.filter(balance__lte=Decimal(max_balance))
    
    # Pagination
    paginator = Paginator(accounts, 25)
    page_number = request.GET.get('page')
    accounts = paginator.get_page(page_number)
    
    # Get filter options
    products = SavingsProduct.objects.filter(is_active=True)
    
    context = {
        'accounts': accounts,
        'products': products,
        'search_query': search_query,
        'product_id': product_id,
        'status_filter': status_filter,
        'min_balance': min_balance,
        'max_balance': max_balance,
        'account_statuses': SavingsAccount._meta.get_field('status').choices,
        'title': 'Savings Accounts',
        'page_title': 'Savings Accounts',
    }
    
    return render(request, 'savings/account_list.html', context)


@login_required
def account_detail(request, account_id):
    """View savings account details."""
    account = get_object_or_404(SavingsAccount, id=account_id)
    
    # Get recent transactions
    transactions = account.transactions.order_by('-created_at')[:20]
    
    # Get interest calculations
    interest_calculations = account.interest_calculations.order_by('-calculation_date')[:10]
    
    # Get active holds
    active_holds = account.holds.filter(status='active').order_by('-created_at')
    
    # Calculate statistics
    stats = {
        'total_deposits': account.transactions.filter(
            transaction_type='deposit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'total_withdrawals': account.transactions.filter(
            transaction_type='withdrawal'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'transaction_count': account.transactions.count(),
        'average_balance': account.transactions.aggregate(
            avg=Avg('balance_after')
        )['avg'] or Decimal('0.00'),
    }
    
    # Check loan eligibility for common loan categories
    loan_eligibility = {}
    common_loan_categories = ['personal', 'business', 'emergency', 'agricultural']
    for loan_category in common_loan_categories:
        is_eligible, message = account.check_loan_eligibility(loan_category, Decimal('10000'))
        loan_eligibility[loan_category] = {
            'eligible': is_eligible,
            'message': message
        }
    
    context = {
        'account': account,
        'transactions': transactions,
        'interest_calculations': interest_calculations,
        'active_holds': active_holds,
        'stats': stats,
        'loan_eligibility': loan_eligibility,
        'title': f'Account - {account.account_number}',
        'page_title': account.account_number,
    }
    
    return render(request, 'savings/account_detail.html', context)


@login_required
def open_account(request):
    """Open new savings account."""
    if request.method == 'POST':
        # This will be implemented with forms
        pass
    
    borrowers = Borrower.objects.filter(status='active').order_by('first_name', 'last_name')
    products = SavingsProduct.objects.filter(is_active=True)
    
    context = {
        'borrowers': borrowers,
        'products': products,
        'title': 'Open Savings Account',
        'page_title': 'New Account',
    }
    
    return render(request, 'savings/open_account.html', context)


@login_required
def process_transaction(request):
    """Process deposit or withdrawal transaction."""
    if request.method == 'POST':
        # This will be implemented with forms
        pass
    
    accounts = SavingsAccount.objects.filter(
        status='active'
    ).select_related('borrower').order_by('account_number')
    
    context = {
        'accounts': accounts,
        'title': 'Process Transaction',
        'page_title': 'New Transaction',
    }
    
    return render(request, 'savings/process_transaction.html', context)


@login_required
def transaction_list(request):
    """List all savings transactions."""
    transactions = SavingsTransaction.objects.select_related(
        'savings_account__borrower', 'processed_by'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(savings_account__account_number__icontains=search_query) |
            Q(savings_account__borrower__first_name__icontains=search_query) |
            Q(savings_account__borrower__last_name__icontains=search_query)
        )
    
    # Filter by transaction type
    transaction_type = request.GET.get('type', '')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    context = {
        'transactions': transactions,
        'search_query': search_query,
        'transaction_type': transaction_type,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_types': SavingsTransaction._meta.get_field('transaction_type').choices,
        'transaction_statuses': SavingsTransaction._meta.get_field('status').choices,
        'title': 'Savings Transactions',
        'page_title': 'Transactions',
    }
    
    return render(request, 'savings/transaction_list.html', context)


@login_required
def interest_calculation(request):
    """Calculate and post interest for savings accounts."""
    if request.method == 'POST':
        # This will be implemented with forms
        pass

    # Get accounts eligible for interest calculation
    eligible_accounts = SavingsAccount.objects.filter(
        status='active',
        balance__gt=0
    ).select_related('borrower', 'savings_product')

    # Get pending interest calculations
    pending_calculations = SavingsInterestCalculation.objects.filter(
        is_posted=False
    ).select_related('savings_account__borrower').order_by('-calculation_date')

    context = {
        'eligible_accounts': eligible_accounts,
        'pending_calculations': pending_calculations,
        'title': 'Interest Calculation',
        'page_title': 'Interest Management',
    }

    return render(request, 'savings/interest_calculation.html', context)


@login_required
def interest_detail(request, calculation_id):
    """View details of a specific interest calculation."""
    calculation = get_object_or_404(
        SavingsInterestCalculation.objects.select_related(
            'savings_account__borrower', 
            'savings_account__savings_product'
        ), 
        id=calculation_id
    )
    
    context = {
        'calculation': calculation,
        'title': 'Interest Calculation Detail',
        'page_title': f'Interest Calculation #{calculation.id}',
    }
    
    return render(request, 'savings/interest_detail.html', context)


@login_required
def savings_reports(request):
    """Generate savings reports."""
    report_type = request.GET.get('report_type', 'summary')

    if report_type == 'summary':
        # Summary report
        total_accounts = SavingsAccount.objects.count()
        total_balance = SavingsAccount.objects.aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')

        # By product
        by_product = SavingsProduct.objects.annotate(
            account_count=Count('accounts'),
            total_balance=Sum('accounts__balance'),
            avg_balance=Avg('accounts__balance')
        ).filter(account_count__gt=0)

        # By status
        by_status = []
        for status_code, status_label in SavingsAccount._meta.get_field('status').choices:
            count = SavingsAccount.objects.filter(status=status_code).count()
            balance = SavingsAccount.objects.filter(status=status_code).aggregate(
                total=Sum('balance')
            )['total'] or Decimal('0.00')

            if count > 0:
                by_status.append({
                    'status': status_label,
                    'count': count,
                    'balance': balance
                })

        report_data = {
            'total_accounts': total_accounts,
            'total_balance': total_balance,
            'by_product': by_product,
            'by_status': by_status,
        }

    elif report_type == 'transactions':
        # Transaction report
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)

        transaction_summary = {
            'total_deposits': SavingsTransaction.objects.filter(
                transaction_type='deposit',
                transaction_date__gte=last_30_days
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'total_withdrawals': SavingsTransaction.objects.filter(
                transaction_type='withdrawal',
                transaction_date__gte=last_30_days
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'deposit_count': SavingsTransaction.objects.filter(
                transaction_type='deposit',
                transaction_date__gte=last_30_days
            ).count(),
            'withdrawal_count': SavingsTransaction.objects.filter(
                transaction_type='withdrawal',
                transaction_date__gte=last_30_days
            ).count(),
        }

        # Daily transaction volumes
        daily_transactions = []
        for i in range(30):
            date = today - timedelta(days=i)
            deposits = SavingsTransaction.objects.filter(
                transaction_type='deposit',
                transaction_date=date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            withdrawals = SavingsTransaction.objects.filter(
                transaction_type='withdrawal',
                transaction_date=date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            daily_transactions.append({
                'date': date,
                'deposits': deposits,
                'withdrawals': withdrawals,
                'net': deposits - withdrawals
            })

        report_data = {
            'transaction_summary': transaction_summary,
            'daily_transactions': daily_transactions,
        }

    else:
        # Interest report
        total_interest_accrued = SavingsAccount.objects.aggregate(
            total=Sum('accrued_interest')
        )['total'] or Decimal('0.00')

        total_interest_earned = SavingsAccount.objects.aggregate(
            total=Sum('total_interest_earned')
        )['total'] or Decimal('0.00')

        # Interest by product
        interest_by_product = SavingsProduct.objects.annotate(
            total_accrued=Sum('accounts__accrued_interest'),
            total_earned=Sum('accounts__total_interest_earned'),
            account_count=Count('accounts')
        ).filter(account_count__gt=0)

        # Recent interest calculations
        recent_calculations = SavingsInterestCalculation.objects.select_related(
            'savings_account__borrower'
        ).order_by('-calculation_date')[:20]

        report_data = {
            'total_interest_accrued': total_interest_accrued,
            'total_interest_earned': total_interest_earned,
            'interest_by_product': interest_by_product,
            'recent_calculations': recent_calculations,
        }

    context = {
        'report_type': report_type,
        'report_data': report_data,
        'title': 'Savings Reports',
        'page_title': 'Savings Reports',
    }

    return render(request, 'savings/reports.html', context)


@login_required
def check_loan_eligibility_api(request):
    """API endpoint to check loan eligibility for a savings account."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            account_id = data.get('account_id')
            loan_category = data.get('loan_category')
            loan_amount = Decimal(str(data.get('loan_amount', '0')))

            account = get_object_or_404(SavingsAccount, id=account_id)
            is_eligible, message = account.check_loan_eligibility(loan_category, loan_amount)

            return JsonResponse({
                'eligible': is_eligible,
                'message': message,
                'account_balance': float(account.balance),
                'minimum_balance': float(account.minimum_balance_required)
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def account_balance_api(request, account_number):
    """API endpoint to get account balance."""
    try:
        account = get_object_or_404(SavingsAccount, account_number=account_number)

        return JsonResponse({
            'account_number': account.account_number,
            'balance': float(account.balance),
            'available_balance': float(account.available_balance),
            'minimum_balance': float(account.minimum_balance_required),
            'status': account.status,
            'borrower_name': account.borrower.get_full_name(),
            'product_name': account.savings_product.name
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required
def generate_report(request):
    """Generate savings reports based on report type and date range."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    try:
        report_type = request.POST.get('report_type')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        branch = request.POST.get('branch', '')
        
        # Validate required fields
        if not all([report_type, date_from, date_to]):
            return JsonResponse({
                'success': False, 
                'message': 'Please provide all required fields'
            })
        
        # Parse dates
        from datetime import datetime
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date format'
            })
        
        # Generate report based on type
        context = {
            'report_type': report_type,
            'date_from': date_from,
            'date_to': date_to,
            'branch': branch,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        if report_type == 'account_summary':
            accounts = SavingsAccount.objects.filter(
                created_at__date__range=[start_date.date(), end_date.date()]
            )
            if branch:
                # Add branch filter if implemented
                pass
            
            context.update({
                'accounts': accounts,
                'total_accounts': accounts.count(),
                'total_balance': accounts.aggregate(Sum('balance'))['balance__sum'] or 0,
                'active_accounts': accounts.filter(status='active').count(),
            })
            
        elif report_type == 'transaction_summary':
            transactions = SavingsTransaction.objects.filter(
                transaction_date__date__range=[start_date.date(), end_date.date()]
            )
            if branch:
                # Add branch filter if implemented
                pass
            
            context.update({
                'transactions': transactions,
                'total_transactions': transactions.count(),
                'total_deposits': transactions.filter(transaction_type='deposit').aggregate(Sum('amount'))['amount__sum'] or 0,
                'total_withdrawals': transactions.filter(transaction_type='withdrawal').aggregate(Sum('amount'))['amount__sum'] or 0,
                'total_charges': transactions.filter(transaction_type='charges').aggregate(Sum('amount'))['amount__sum'] or 0,
            })
            
        elif report_type == 'interest_summary':
            interest_calculations = SavingsInterestCalculation.objects.filter(
                calculation_date__date__range=[start_date.date(), end_date.date()]
            )
            
            context.update({
                'interest_calculations': interest_calculations,
                'total_interest': interest_calculations.aggregate(Sum('interest_amount'))['interest_amount__sum'] or 0,
                'accounts_with_interest': interest_calculations.values('savings_account').distinct().count(),
            })
            
        elif report_type == 'balance_summary':
            accounts = SavingsAccount.objects.all()
            if branch:
                # Add branch filter if implemented
                pass
            
            context.update({
                'accounts': accounts,
                'total_balance': accounts.aggregate(Sum('balance'))['balance__sum'] or 0,
                'average_balance': accounts.aggregate(Avg('balance'))['balance__avg'] or 0,
                'minimum_balance': accounts.aggregate(Min('balance'))['balance__min'] or 0,
                'maximum_balance': accounts.aggregate(Max('balance'))['balance__max'] or 0,
            })
        
        # Render the report template
        from django.template.loader import render_to_string
        html_content = render_to_string('savings/report_content.html', context, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html_content
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error generating report: {str(e)}'
        })


