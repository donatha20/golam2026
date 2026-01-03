from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from datetime import datetime, timedelta
from django_tables2 import RequestConfig
from .models import Income, Expenditure, IncomeCategory, ExpenditureCategory, Capital, Shareholder
from .forms import (
    IncomeForm, ExpenditureForm, IncomeCategoryForm, ExpenditureCategoryForm,
    IncomeFilterForm, ExpenditureFilterForm, ShareholderForm, CapitalForm, 
    CapitalInjectionForm, CapitalWithdrawalForm
)
from .tables import IncomeTable, ExpenditureTable, IncomeCategoryTable, ExpenditureCategoryTable
from .filters import IncomeFilter, ExpenditureFilter, CategoryFilter
from .services import get_account_balances, AccountingService
from apps.accounts.models import UserActivity


@login_required
def add_income(request):
    """Add new income record using Django forms."""
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.recorded_by = request.user
            income.save()

            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE',
                object_id=income.id,
                description=f'Added income: {income.get_source_display()} - ₹{income.amount:,.2f}',
                content_type='Income',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )

            messages.success(request, f'Income record added successfully! ID: {income.income_id}')
            return redirect('finance_tracker:add_income')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = IncomeForm()

    # Get recent income records and statistics
    recent_income = Income.objects.select_related('category').order_by('-created_at')[:10]

    # Get account balances
    account_balances = get_account_balances()

    # Monthly statistics
    current_month = timezone.now().replace(day=1)
    monthly_stats = {
        'this_month': Income.objects.filter(
            income_date__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'last_month': Income.objects.filter(
            income_date__gte=current_month - timedelta(days=32),
            income_date__lt=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_records': Income.objects.count(),
    }

    context = {
        'form': form,
        'recent_income': recent_income,
        'account_balances': account_balances,
        'monthly_stats': monthly_stats,
        'title': 'Add Income Record',
        'page_title': 'Record New Income',
    }

    return render(request, 'finance_tracker/add_income.html', context)


@login_required
def view_income(request):
    """View all income records with filtering and search."""
    # Get all income records
    income_queryset = Income.objects.select_related('category', 'recorded_by').order_by('-income_date', '-created_at')

    # Apply filters using django-filter
    income_filter = IncomeFilter(request.GET, queryset=income_queryset)
    income_records = income_filter.qs

    # Create data table
    table = IncomeTable(income_records)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    # Statistics
    current_year = timezone.now().year
    current_month = timezone.now().month

    stats = {
        'total_records': Income.objects.count(),
        'total_amount': Income.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'this_month': Income.objects.filter(
            income_date__month=current_month,
            income_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'this_year': Income.objects.filter(
            income_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'avg_amount': Income.objects.aggregate(avg=Sum('amount'))['avg'] or 0,
    }

    # Category breakdown
    category_stats = Income.objects.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]

    context = {
        'table': table,
        'filter': income_filter,
        'stats': stats,
        'category_stats': category_stats,
        'title': 'Income Records',
        'page_title': 'View Income Records',
    }

    return render(request, 'finance_tracker/view_income.html', context)


@login_required
def add_expenditure(request):
    """Add new expenditure record using Django forms."""
    if request.method == 'POST':
        form = ExpenditureForm(request.POST)
        if form.is_valid():
            expenditure = form.save(commit=False)
            expenditure.recorded_by = request.user
            expenditure.save()

            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE',
                object_id=expenditure.id,
                description=f'Added expenditure: {expenditure.get_expenditure_type_display()} - ₹{expenditure.amount:,.2f}',
                content_type='Expenditure',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )

            messages.success(request, f'Expenditure record added successfully! ID: {expenditure.expenditure_id}')
            return redirect('finance_tracker:add_expenditure')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenditureForm()

    # Get recent expenditure records and statistics
    recent_expenditures = Expenditure.objects.select_related('category').order_by('-created_at')[:10]

    # Get account balances
    account_balances = get_account_balances()

    # Monthly statistics
    current_month = timezone.now().replace(day=1)
    monthly_stats = {
        'this_month': Expenditure.objects.filter(
            expenditure_date__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'last_month': Expenditure.objects.filter(
            expenditure_date__gte=current_month - timedelta(days=32),
            expenditure_date__lt=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending_approval': Expenditure.objects.filter(status='pending').count(),
        'total_records': Expenditure.objects.count(),
    }

    context = {
        'form': form,
        'recent_expenditures': recent_expenditures,
        'account_balances': account_balances,
        'monthly_stats': monthly_stats,
        'title': 'Add Expenditure Record',
        'page_title': 'Record New Expenditure',
    }

    return render(request, 'finance_tracker/add_expenditure.html', context)


@login_required
def view_expenditures(request):
    """View all expenditure records with filtering and search."""
    # Get all expenditure records
    expenditure_queryset = Expenditure.objects.select_related('category', 'recorded_by').order_by('-expenditure_date', '-created_at')

    # Apply filters using django-filter
    expenditure_filter = ExpenditureFilter(request.GET, queryset=expenditure_queryset)
    expenditures = expenditure_filter.qs

    # Create data table
    table = ExpenditureTable(expenditures)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    # Statistics
    current_year = timezone.now().year
    current_month = timezone.now().month

    stats = {
        'total_records': Expenditure.objects.count(),
        'total_amount': Expenditure.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'pending_approval': Expenditure.objects.filter(status='pending').count(),
        'this_month': Expenditure.objects.filter(
            expenditure_date__month=current_month,
            expenditure_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'this_year': Expenditure.objects.filter(
            expenditure_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }

    # Category breakdown
    category_stats = Expenditure.objects.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]

    # Status breakdown
    status_stats = Expenditure.objects.values('status').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    context = {
        'table': table,
        'filter_form': filter_form,
        'stats': stats,
        'category_stats': category_stats,
        'status_stats': status_stats,
        'title': 'Expenditure Records',
        'page_title': 'View Expenditure Records',
    }

    return render(request, 'finance_tracker/view_expenditures.html', context)


@login_required
def dashboard(request):
    """Finance tracker dashboard with analytics."""
    # Get account balances
    account_balances = get_account_balances()

    # Date ranges
    today = timezone.now().date()
    current_month = today.replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    current_year = today.replace(month=1, day=1)

    # Income statistics
    income_stats = {
        'total': Income.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'this_month': Income.objects.filter(
            income_date__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'last_month': Income.objects.filter(
            income_date__gte=last_month,
            income_date__lt=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'this_year': Income.objects.filter(
            income_date__gte=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'count': Income.objects.count(),
    }

    # Expenditure statistics
    expenditure_stats = {
        'total': Expenditure.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'this_month': Expenditure.objects.filter(
            expenditure_date__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'last_month': Expenditure.objects.filter(
            expenditure_date__gte=last_month,
            expenditure_date__lt=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'this_year': Expenditure.objects.filter(
            expenditure_date__gte=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending': Expenditure.objects.filter(status='pending').count(),
        'count': Expenditure.objects.count(),
    }

    # Calculate net income
    net_income = {
        'this_month': income_stats['this_month'] - expenditure_stats['this_month'],
        'last_month': income_stats['last_month'] - expenditure_stats['last_month'],
        'this_year': income_stats['this_year'] - expenditure_stats['this_year'],
        'total': income_stats['total'] - expenditure_stats['total'],
    }

    # Recent transactions
    recent_income = Income.objects.select_related('category').order_by('-created_at')[:5]
    recent_expenditures = Expenditure.objects.select_related('category').order_by('-created_at')[:5]

    # Top categories
    top_income_categories = Income.objects.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    top_expenditure_categories = Expenditure.objects.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    context = {
        'account_balances': account_balances,
        'income_stats': income_stats,
        'expenditure_stats': expenditure_stats,
        'net_income': net_income,
        'recent_income': recent_income,
        'recent_expenditures': recent_expenditures,
        'top_income_categories': top_income_categories,
        'top_expenditure_categories': top_expenditure_categories,
        'title': 'Finance Dashboard',
        'page_title': 'Financial Overview',
    }

    return render(request, 'finance_tracker/dashboard.html', context)


@login_required
def manage_income_categories(request):
    """Manage income categories."""
    if request.method == 'POST':
        form = IncomeCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Income category "{category.name}" created successfully!')
            return redirect('finance_tracker:manage_income_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = IncomeCategoryForm()

    categories = IncomeCategory.objects.order_by('name')

    # Create data table
    table = IncomeCategoryTable(categories)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    context = {
        'form': form,
        'table': table,
        'title': 'Manage Income Categories',
        'page_title': 'Income Categories',
    }

    return render(request, 'finance_tracker/manage_income_categories.html', context)


@login_required
def manage_expenditure_categories(request):
    """Manage expenditure categories."""
    if request.method == 'POST':
        form = ExpenditureCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Expenditure category "{category.name}" created successfully!')
            return redirect('finance_tracker:manage_expenditure_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenditureCategoryForm()

    categories = ExpenditureCategory.objects.order_by('name')

    # Create data table
    table = ExpenditureCategoryTable(categories)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    context = {
        'form': form,
        'table': table,
        'title': 'Manage Expenditure Categories',
        'page_title': 'Expenditure Categories',
    }

    return render(request, 'finance_tracker/manage_expenditure_categories.html', context)


@login_required
def approve_expenditure(request, expenditure_id):
    """Approve a pending expenditure."""
    expenditure = get_object_or_404(Expenditure, id=expenditure_id, status='pending')

    if request.method == 'POST':
        expenditure.status = 'approved'
        expenditure.approved_by = request.user
        expenditure.approval_date = timezone.now()
        expenditure.save()

        messages.success(request, f'Expenditure {expenditure.expenditure_id} approved successfully!')
        return redirect('finance_tracker:view_expenditures')

    context = {
        'expenditure': expenditure,
        'title': f'Approve Expenditure {expenditure.expenditure_id}',
    }

    return render(request, 'finance_tracker/approve_expenditure.html', context)


@login_required
def financial_summary_api(request):
    """API endpoint for financial summary data."""
    account_balances = get_account_balances()

    # Monthly data for charts
    monthly_data = []
    for i in range(12):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        income_total = Income.objects.filter(
            income_date__gte=month_start,
            income_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0

        expenditure_total = Expenditure.objects.filter(
            expenditure_date__gte=month_start,
            expenditure_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_data.append({
            'month': month_start.strftime('%Y-%m'),
            'income': float(income_total),
            'expenditure': float(expenditure_total),
            'net': float(income_total - expenditure_total)
        })

    return JsonResponse({
        'account_balances': {k: float(v) for k, v in account_balances.items()},
        'monthly_data': list(reversed(monthly_data))
    })


# ============ CAPITAL MANAGEMENT VIEWS ============

@login_required
def shareholder_list(request):
    """List all shareholders."""
    shareholders = Shareholder.objects.all().order_by('name')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        shareholders = shareholders.filter(
            Q(name__icontains=search_query) |
            Q(shareholder_id__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(shareholders, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    stats = {
        'total_shareholders': Shareholder.objects.count(),
        'active_shareholders': Shareholder.objects.filter(status='active').count(),
        'total_shares': Shareholder.objects.aggregate(Sum('shares_owned'))['shares_owned__sum'] or 0,
        'total_investment': Shareholder.objects.aggregate(Sum('total_investment'))['total_investment__sum'] or 0,
    }

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'stats': stats,
    }
    return render(request, 'finance_tracker/shareholder_list.html', context)


@login_required
def add_shareholder(request):
    """Add new shareholder."""
    if request.method == 'POST':
        form = ShareholderForm(request.POST)
        if form.is_valid():
            shareholder = form.save(commit=False)
            shareholder.created_by = request.user
            shareholder.save()

            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE',
                object_id=shareholder.id,
                description=f'Added shareholder: {shareholder.name}',
                content_type='Shareholder',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )

            messages.success(request, f'Shareholder {shareholder.name} added successfully!')
            return redirect('finance_tracker:shareholder_list')
    else:
        form = ShareholderForm()

    return render(request, 'finance_tracker/add_shareholder.html', {'form': form})


@login_required
def capital_list(request):
    """List all capital transactions."""
    capital_transactions = Capital.objects.select_related('shareholder', 'created_by').order_by('-transaction_date')

    # Filter functionality
    capital_type = request.GET.get('capital_type', '')
    transaction_type = request.GET.get('transaction_type', '')
    status = request.GET.get('status', '')

    if capital_type:
        capital_transactions = capital_transactions.filter(capital_type=capital_type)
    if transaction_type:
        capital_transactions = capital_transactions.filter(transaction_type=transaction_type)
    if status:
        capital_transactions = capital_transactions.filter(status=status)

    # Pagination
    paginator = Paginator(capital_transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    stats = {
        'total_capital': Capital.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_capital': Capital.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_transactions': Capital.objects.count(),
    }

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'capital_type_choices': Capital.CAPITAL_TYPE_CHOICES,
        'transaction_type_choices': Capital.TRANSACTION_TYPE_CHOICES,
        'status_choices': Capital.STATUS_CHOICES,
        'filters': {
            'capital_type': capital_type,
            'transaction_type': transaction_type,
            'status': status,
        }
    }
    return render(request, 'finance_tracker/capital_list.html', context)


@login_required
def add_capital(request):
    """Add new capital injection."""
    if request.method == 'POST':
        form = CapitalInjectionForm(request.POST)
        if form.is_valid():
            capital = form.save(commit=False)
            capital.transaction_type = 'injection'  # Force injection type
            capital.created_by = request.user
            capital.save()

            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE',
                object_id=capital.id,
                description=f'Added capital injection: {capital.get_capital_type_display()} - ₹{capital.amount:,.2f}',
                content_type='Capital',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )

            messages.success(request, f'Capital injection added successfully! ID: {capital.capital_id}')
            return redirect('finance_tracker:capital_list')
        else:
            # More detailed error message
            error_details = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_details.append(f"{field}: {error}")
            
            if error_details:
                messages.error(request, f'Form validation failed: {", ".join(error_details)}')
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = CapitalInjectionForm()

    # Get recent capital transactions and statistics
    recent_capital = Capital.objects.select_related('shareholder').order_by('-created_at')[:10]

    # Get account balances
    account_balances = get_account_balances()

    # Capital statistics
    capital_stats = {
        'total_capital': Capital.objects.filter(
            status='completed', 
            transaction_type='injection'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_withdrawals': Capital.objects.filter(
            status='completed',
            transaction_type='withdrawal'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending_capital': Capital.objects.filter(status='pending').count(),
        'total_shareholders': Shareholder.objects.filter(status='active').count(),
    }

    context = {
        'form': form,
        'recent_capital': recent_capital,
        'account_balances': account_balances,
        'capital_stats': capital_stats,
        'title': 'Add Capital Injection',
        'page_title': 'Record Capital Injection',
        'transaction_type': 'injection',
    }

    return render(request, 'finance_tracker/add_capital.html', context)


@login_required
def withdraw_capital(request):
    """Withdraw capital."""
    if request.method == 'POST':
        form = CapitalWithdrawalForm(request.POST)
        if form.is_valid():
            capital = form.save(commit=False)
            capital.transaction_type = 'withdrawal'  # Force withdrawal type
            capital.created_by = request.user
            capital.save()

            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE',
                object_id=capital.id,
                description=f'Added capital withdrawal: {capital.get_capital_type_display()} - ₹{capital.amount:,.2f}',
                content_type='Capital',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )

            messages.success(request, f'Capital withdrawal recorded successfully! ID: {capital.capital_id}')
            return redirect('finance_tracker:capital_list')
        else:
            # More detailed error message
            error_details = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_details.append(f"{field}: {error}")
            
            if error_details:
                messages.error(request, f'Form validation failed: {", ".join(error_details)}')
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = CapitalWithdrawalForm()

    # Get recent capital transactions and statistics
    recent_capital = Capital.objects.select_related('shareholder').order_by('-created_at')[:10]

    # Get account balances
    account_balances = get_account_balances()

    # Capital statistics
    capital_stats = {
        'total_capital': Capital.objects.filter(
            status='completed', 
            transaction_type='injection'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_withdrawals': Capital.objects.filter(
            status='completed',
            transaction_type='withdrawal'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending_capital': Capital.objects.filter(status='pending').count(),
        'total_shareholders': Shareholder.objects.filter(status='active').count(),
    }

    context = {
        'form': form,
        'recent_capital': recent_capital,
        'account_balances': account_balances,
        'capital_stats': capital_stats,
        'title': 'Withdraw Capital',
        'page_title': 'Record Capital Withdrawal',
        'transaction_type': 'withdrawal',
    }

    return render(request, 'finance_tracker/withdraw_capital.html', context)


@login_required
def capital_approval_list(request):
    """List all capital transactions pending approval."""
    pending_capital = Capital.objects.filter(status='pending').select_related('created_by', 'shareholder').order_by('-created_at')
    
    context = {
        'pending_capital': pending_capital,
        'total_pending': pending_capital.count(),
        'total_pending_amount': pending_capital.aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    return render(request, 'finance_tracker/capital_approval_list.html', context)


@login_required
def approve_capital(request, capital_id):
    """Approve a capital transaction."""
    capital = get_object_or_404(Capital, id=capital_id, status='pending')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comments = request.POST.get('comments', '')
        
        if action == 'approve':
            capital.status = 'approved'
            capital.approved_by = request.user
            capital.approval_date = timezone.now()
            capital.save()
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='APPROVE',
                object_id=capital.id,
                description=f'Approved capital {capital.get_transaction_type_display().lower()}: {capital.get_capital_type_display()} - ₹{capital.amount:,.2f}',
                content_type='Capital',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Capital {capital.get_transaction_type_display().lower()} approved successfully!')
            
        elif action == 'reject':
            capital.status = 'cancelled'
            capital.approved_by = request.user
            capital.approval_date = timezone.now()
            capital.save()
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='REJECT',
                object_id=capital.id,
                description=f'Rejected capital {capital.get_transaction_type_display().lower()}: {capital.get_capital_type_display()} - ₹{capital.amount:,.2f}. Reason: {comments}',
                content_type='Capital',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.warning(request, f'Capital {capital.get_transaction_type_display().lower()} rejected.')
        
        return redirect('finance_tracker:capital_approval_list')
    
    context = {
        'capital': capital,
    }
    
    return render(request, 'finance_tracker/approve_capital.html', context)


@login_required
def capital_approval_detail(request, capital_id):
    """View details of a capital transaction for approval."""
    capital = get_object_or_404(Capital, id=capital_id)
    
    context = {
        'capital': capital,
    }
    
    return render(request, 'finance_tracker/capital_approval_detail.html', context)


@login_required
def retained_earnings(request):
    """Calculate and display retained earnings."""
    # Get date range parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to current year if no dates provided
    if not start_date or not end_date:
        current_year = timezone.now().year
        start_date = f"{current_year}-01-01"
        end_date = f"{current_year}-12-31"
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
        start_date = timezone.now().date().replace(month=1, day=1)
        end_date = timezone.now().date().replace(month=12, day=31)
    
    # Calculate total income for the period
    total_income = Income.objects.filter(
        income_date__gte=start_date,
        income_date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate total expenditures for the period
    total_expenditure = Expenditure.objects.filter(
        expenditure_date__gte=start_date,
        expenditure_date__lte=end_date,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate net income for the period
    period_net_income = total_income - total_expenditure
    
    # Calculate cumulative retained earnings (all-time)
    cumulative_income = Income.objects.filter(
        income_date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    cumulative_expenditure = Expenditure.objects.filter(
        expenditure_date__lte=end_date,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Get capital withdrawals (dividends/distributions)
    capital_withdrawals = Capital.objects.filter(
        transaction_type='withdrawal',
        status__in=['approved', 'completed'],
        transaction_date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate retained earnings = Cumulative Net Income - Capital Withdrawals
    cumulative_retained_earnings = (cumulative_income - cumulative_expenditure) - capital_withdrawals
    
    # Monthly breakdown for the current year
    monthly_data = []
    current_year = end_date.year
    for month in range(1, 13):
        month_start = timezone.now().date().replace(year=current_year, month=month, day=1)
        
        # Calculate last day of month
        if month == 12:
            month_end = month_start.replace(year=current_year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month + 1, day=1) - timedelta(days=1)
        
        # Don't calculate future months
        if month_start > timezone.now().date():
            break
            
        month_income = Income.objects.filter(
            income_date__gte=month_start,
            income_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_expenditure = Expenditure.objects.filter(
            expenditure_date__gte=month_start,
            expenditure_date__lte=month_end,
            status__in=['approved', 'completed']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_net = month_income - month_expenditure
        
        monthly_data.append({
            'month': month_start.strftime('%B'),
            'month_num': month,
            'income': month_income,
            'expenditure': month_expenditure,
            'net_income': month_net,
        })
    
    # Year-over-year comparison
    yearly_data = []
    for year in range(current_year - 4, current_year + 1):
        year_start = timezone.now().date().replace(year=year, month=1, day=1)
        year_end = timezone.now().date().replace(year=year, month=12, day=31)
        
        year_income = Income.objects.filter(
            income_date__gte=year_start,
            income_date__lte=year_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        year_expenditure = Expenditure.objects.filter(
            expenditure_date__gte=year_start,
            expenditure_date__lte=year_end,
            status__in=['approved', 'completed']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        year_withdrawals = Capital.objects.filter(
            transaction_type='withdrawal',
            status__in=['approved', 'completed'],
            transaction_date__gte=year_start,
            transaction_date__lte=year_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        yearly_data.append({
            'year': year,
            'income': year_income,
            'expenditure': year_expenditure,
            'net_income': year_income - year_expenditure,
            'withdrawals': year_withdrawals,
            'retained': (year_income - year_expenditure) - year_withdrawals,
        })
    
    # Key financial ratios
    total_capital_injections = Capital.objects.filter(
        transaction_type='injection',
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Return on Equity (ROE) approximation
    if total_capital_injections > 0:
        roe = (period_net_income / total_capital_injections) * 100
    else:
        roe = 0
    
    # Profit margin
    if total_income > 0:
        profit_margin = (period_net_income / total_income) * 100
    else:
        profit_margin = 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'period_stats': {
            'total_income': total_income,
            'total_expenditure': total_expenditure,
            'net_income': period_net_income,
            'profit_margin': profit_margin,
        },
        'retained_earnings': {
            'cumulative': cumulative_retained_earnings,
            'capital_withdrawals': capital_withdrawals,
            'total_capital_injections': total_capital_injections,
        },
        'monthly_data': monthly_data,
        'yearly_data': yearly_data,
        'financial_ratios': {
            'roe': roe,
            'profit_margin': profit_margin,
        },
        'title': 'Retained Earnings Analysis',
        'page_title': 'Retained Earnings & Financial Analysis',
    }
    
    return render(request, 'finance_tracker/retained_earnings.html', context)


@login_required
def retained_earnings_api(request):
    """API endpoint for retained earnings data (for charts/widgets)."""
    # Get last 12 months of data
    monthly_retained_earnings = []
    
    for i in range(12):
        month_date = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        month_end = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        # Calculate cumulative retained earnings up to this month
        cumulative_income = Income.objects.filter(
            income_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        cumulative_expenditure = Expenditure.objects.filter(
            expenditure_date__lte=month_end,
            status__in=['approved', 'completed']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        cumulative_withdrawals = Capital.objects.filter(
            transaction_type='withdrawal',
            status__in=['approved', 'completed'],
            transaction_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        retained_earnings = (cumulative_income - cumulative_expenditure) - cumulative_withdrawals
        
        monthly_retained_earnings.append({
            'month': month_date.strftime('%Y-%m'),
            'month_name': month_date.strftime('%B %Y'),
            'retained_earnings': float(retained_earnings),
            'cumulative_income': float(cumulative_income),
            'cumulative_expenditure': float(cumulative_expenditure),
            'cumulative_withdrawals': float(cumulative_withdrawals),
        })
    
    # Current retained earnings summary
    current_date = timezone.now().date()
    current_retained_earnings = monthly_retained_earnings[0] if monthly_retained_earnings else {
        'retained_earnings': 0,
        'cumulative_income': 0,
        'cumulative_expenditure': 0,
        'cumulative_withdrawals': 0,
    }
    
    return JsonResponse({
        'current_retained_earnings': current_retained_earnings['retained_earnings'],
        'monthly_data': list(reversed(monthly_retained_earnings)),
        'summary': {
            'total_income': current_retained_earnings['cumulative_income'],
            'total_expenditure': current_retained_earnings['cumulative_expenditure'],
            'total_withdrawals': current_retained_earnings['cumulative_withdrawals'],
            'retained_earnings': current_retained_earnings['retained_earnings'],
        }
    })
