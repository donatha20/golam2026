"""
Core views for the microfinance system.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.conf import settings
from datetime import datetime, timedelta
import json

from apps.borrowers.models import Borrower
from apps.loans.models import Loan
from apps.repayments.models import Payment
from apps.savings.models import SavingsAccount
from apps.accounts.models import CustomUser, UserActivity, UserSession, UserRole
from django_tables2 import RequestConfig
from .tables import UserTable, UserActivityTable, UserSessionTable


def home(request):
    """
    Landing page for Golam Financial Services.
    """
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    return render(request, 'home.html')


def register(request):
    """
    User registration view.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        # Handle registration form submission
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Basic validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'registration/register.html')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'registration/register.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'registration/register.html')

        try:
            # Create new user
            # For testing: Set AUTO_APPROVE_USERS=True in settings to skip approval
            auto_approve = getattr(settings, 'AUTO_APPROVE_USERS', False)

            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                is_active=auto_approve  # Auto-approve if enabled, otherwise requires admin approval
            )

            if auto_approve:
                messages.success(
                    request,
                    'Account created successfully! You can now log in with your credentials.'
                )
            else:
                messages.success(
                    request,
                    'Account created successfully! Please wait for admin approval. '
                    'You will receive an email notification once your account is activated.'
                )
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'registration/register.html')

    return render(request, 'registration/register.html')


@login_required
def dashboard(request):
    """
    Main dashboard view for Golam Financial Services.
    """
    today = timezone.now().date()
    this_month = today.replace(day=1)
    
    # Import new models with error handling
    try:
        from apps.finance_tracker.models import Income, Expenditure, Capital, Grant, Shareholder
        from .models import SystemSetting, CompanyProfile, Branch

        # Create default system settings if they don't exist
        default_settings = [
            ('company_name', 'Golam Financial Services', 'text', 'Company name displayed in the system', 'general'),
            ('default_currency', 'INR', 'text', 'Default currency for the system', 'general'),
            ('max_loan_amount', '1000000', 'number', 'Maximum loan amount allowed', 'loans'),
            ('default_interest_rate', '18.0', 'number', 'Default interest rate for loans', 'loans'),
            ('enable_sms_notifications', 'true', 'boolean', 'Enable SMS notifications', 'notifications'),
            ('enable_email_notifications', 'true', 'boolean', 'Enable email notifications', 'notifications'),
        ]

        for key, value, setting_type, description, category in default_settings:
            SystemSetting.objects.get_or_create(
                key=key,
                defaults={
                    'value': value,
                    'setting_type': setting_type,
                    'description': description,
                    'category': category,
                    'is_active': True
                }
            )
    except ImportError:
        # If models don't exist, set defaults
        Income = Expenditure = Capital = Grant = Shareholder = None
        SystemSetting = CompanyProfile = Branch = None

    # Calculate dashboard statistics with error handling
    stats = {}

    try:
        # Borrower Statistics
        stats.update({
            'total_borrowers': Borrower.objects.filter(status='active').count(),
            'new_borrowers_this_month': Borrower.objects.filter(
                registration_date__gte=this_month
            ).count(),
        })
    except:
        stats.update({'total_borrowers': 0, 'new_borrowers_this_month': 0})

    try:
        # Loan Statistics
        stats.update({
            'active_loans': Loan.objects.filter(
                status__in=['disbursed', 'active']
            ).count(),
            'total_active_amount': Loan.objects.filter(
                status__in=['disbursed', 'active']
            ).aggregate(total=Sum('amount_approved'))['total'] or 0,
            'overdue_loans': Loan.objects.filter(
                status='active',
                maturity_date__lt=today
            ).count(),
            'overdue_amount': Loan.objects.filter(
                status='active',
                maturity_date__lt=today
            ).aggregate(total=Sum('outstanding_balance'))['total'] or 0,
            'pending_applications': Loan.objects.filter(status='pending').count(),
        })
    except:
        stats.update({
            'active_loans': 0, 'total_active_amount': 0, 'overdue_loans': 0,
            'overdue_amount': 0, 'pending_applications': 0
        })

    try:
        # Payment Statistics
        stats.update({
            'collections_today': Payment.objects.filter(
                payment_date=today
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'payments_today': Payment.objects.filter(
                payment_date=today
            ).count(),
            'monthly_collections': Payment.objects.filter(
                payment_date__gte=this_month
            ).aggregate(total=Sum('amount'))['total'] or 0,
        })
    except:
        stats.update({'collections_today': 0, 'payments_today': 0, 'monthly_collections': 0})

    try:
        # Savings Statistics
        stats.update({
            'total_savings': SavingsAccount.objects.aggregate(
                total=Sum('balance')
            )['total'] or 0,
            'savings_accounts': SavingsAccount.objects.filter(status='active').count(),
            'new_savings_accounts': SavingsAccount.objects.filter(
                opened_date__gte=this_month
            ).count(),
        })
    except:
        stats.update({'total_savings': 0, 'savings_accounts': 0, 'new_savings_accounts': 0})

    try:
        # Finance Tracker Statistics
        if Income and Expenditure:
            stats.update({
                'monthly_income': Income.objects.filter(
                    income_date__gte=this_month,
                    status='RECEIVED'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'monthly_expenses': Expenditure.objects.filter(
                    expenditure_date__gte=this_month,
                    status='paid'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'pending_expenses': Expenditure.objects.filter(
                    status='pending'
                ).count(),
            })
        else:
            stats.update({'monthly_income': 0, 'monthly_expenses': 0, 'pending_expenses': 0})
    except:
        stats.update({'monthly_income': 0, 'monthly_expenses': 0, 'pending_expenses': 0})

    try:
        # Capital & Grants Statistics
        if Capital and Grant and Shareholder:
            stats.update({
                'total_capital': Capital.objects.filter(
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'active_grants': Grant.objects.filter(
                    status__in=['approved', 'received']
                ).count(),
                'total_shareholders': Shareholder.objects.filter(status='active').count(),
                'pending_capital': Capital.objects.filter(status='pending').count(),
            })
        else:
            stats.update({'total_capital': 0, 'active_grants': 0, 'total_shareholders': 0, 'pending_capital': 0})
    except:
        stats.update({'total_capital': 0, 'active_grants': 0, 'total_shareholders': 0, 'pending_capital': 0})

    try:
        # System Statistics
        if Branch and SystemSetting:
            stats.update({
                'total_branches': Branch.objects.filter(is_active=True).count(),
                'system_settings': SystemSetting.objects.filter(is_active=True).count(),
            })
        else:
            stats.update({'total_branches': 0, 'system_settings': 0})
    except:
        stats.update({'total_branches': 0, 'system_settings': 0})
    
    # Recent loan applications (last 10)
    recent_loans = Loan.objects.select_related('borrower').order_by('-created_at')[:10]
    
    # Today's payments (last 10)
    todays_payments = Payment.objects.select_related('borrower').filter(
        payment_date=today
    ).order_by('-processed_date')[:10]
    
    # Portfolio chart data (last 6 months)
    portfolio_data = []
    portfolio_labels = []
    
    for i in range(6):
        month_date = today - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_disbursements = Loan.objects.filter(
            disbursement_date__range=[month_start, month_end]
        ).aggregate(total=Sum('amount_approved'))['total'] or 0
        
        portfolio_data.insert(0, float(month_disbursements))
        portfolio_labels.insert(0, month_date.strftime('%b %Y'))
    
    # Loan status distribution
    status_data = []
    status_labels = []
    
    status_counts = Loan.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    for status_count in status_counts:
        status_labels.append(status_count['status'].title())
        status_data.append(status_count['count'])
    
    context = {
        'today': today,
        'stats': stats,
        'recent_loans': recent_loans,
        'todays_payments': todays_payments,
        'portfolio_data': json.dumps(portfolio_data),
        'portfolio_labels': json.dumps(portfolio_labels),
        'status_data': json.dumps(status_data),
        'status_labels': json.dumps(status_labels),
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def profile(request):
    """
    User profile view.
    """
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })


def handler404(request, exception):
    """
    Custom 404 error handler.
    """
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """
    Custom 500 error handler.
    """
    return render(request, 'errors/500.html', status=500)


# User Management Views
@login_required
def user_list(request):
    """Display list of all users - admin only."""
    if request.user.role != UserRole.ADMIN:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')

    users = CustomUser.objects.all().order_by('-date_joined')

    # Create data table
    table = UserTable(users)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)

    context = {
        'table': table,
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
        'inactive_users': users.filter(is_active=False).count(),
    }
    return render(request, 'users/user_list_table.html', context)


@login_required
def user_logs(request):
    """Display user activity logs."""
    if request.user.role != UserRole.ADMIN:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')

    # Get recent activities and sessions
    activities = UserActivity.objects.select_related('user').order_by('-timestamp')
    sessions = UserSession.objects.select_related('user').order_by('-login_time')

    # Create data tables
    activity_table = UserActivityTable(activities)
    session_table = UserSessionTable(sessions)

    # Configure pagination
    RequestConfig(request, paginate={"per_page": 20}).configure(activity_table)
    RequestConfig(request, paginate={"per_page": 15}).configure(session_table)

    context = {
        'activity_table': activity_table,
        'session_table': session_table,
        'total_activities': activities.count(),
        'active_sessions': sessions.filter(is_active=True).count(),
    }
    return render(request, 'users/user_logs_table.html', context)


@login_required
def add_user(request):
    """Add new user - admin only."""
    if request.user.role != UserRole.ADMIN:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        role = request.POST.get('role', UserRole.LOAN_OFFICER)
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Basic validation
        if not all([username, email, first_name, last_name, password1, password2]):
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'users/add_user.html', {'roles': UserRole.choices})

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/add_user.html', {'roles': UserRole.choices})

        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'users/add_user.html', {'roles': UserRole.choices})

        # Check if username or email already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'users/add_user.html', {'roles': UserRole.choices})

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'users/add_user.html', {'roles': UserRole.choices})

        try:
            # Create new user
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=role,
                is_active=True  # Admin created users are active by default
            )

            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE_USER',
                description=f'Created new user: {user.username} ({user.get_full_name()})',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='CustomUser',
                object_id=user.id
            )

            messages.success(request, f'User {user.username} created successfully!')
            return redirect('core:user_list')

        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')

    context = {
        'roles': UserRole.choices
    }
    return render(request, 'users/add_user.html', context)


# ============ SETTINGS VIEWS ============

@login_required
@login_required
def settings_dashboard(request):
    """Settings dashboard."""
    from .models import SystemSetting, CompanyProfile, Branch, LoanCategory, PenaltyConfiguration

    # Get settings statistics
    stats = {
        'total_settings': SystemSetting.objects.count(),
        'active_settings': SystemSetting.objects.filter(is_active=True).count(),
        'company_profiles': CompanyProfile.objects.count(),
        'branches': Branch.objects.count(),
        'loan_categories': LoanCategory.objects.filter(is_active=True).count(),
        'penalty_configs': PenaltyConfiguration.objects.filter(is_active=True).count(),
    }

    # Get recent settings changes
    recent_settings = SystemSetting.objects.order_by('-updated_at')[:10]

    context = {
        'stats': stats,
        'recent_settings': recent_settings,
    }

    return render(request, 'core/settings_dashboard.html', context)


@login_required
def system_settings(request):
    """Manage system settings."""
    from .models import SystemSetting

    if request.method == 'POST':
        # Handle settings update
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                except SystemSetting.DoesNotExist:
                    pass

        messages.success(request, 'Settings updated successfully!')
        return redirect('core:system_settings')

    # Group settings by category
    settings_by_category = {}
    for setting in SystemSetting.objects.filter(is_active=True).order_by('category', 'key'):
        if setting.category not in settings_by_category:
            settings_by_category[setting.category] = []
        settings_by_category[setting.category].append(setting)

    context = {
        'settings_by_category': settings_by_category,
    }

    return render(request, 'core/system_settings.html', context)


@login_required
def company_profile(request):
    """Manage company profile."""
    from .models import CompanyProfile

    company = CompanyProfile.get_active_company()

    if request.method == 'POST':
        # Handle company profile update
        if company:
            # Update existing profile
            company.name = request.POST.get('name', company.name)
            company.legal_name = request.POST.get('legal_name', company.legal_name)
            company.registration_number = request.POST.get('registration_number', company.registration_number)
            company.tax_id = request.POST.get('tax_id', company.tax_id)
            company.address_line_1 = request.POST.get('address_line_1', company.address_line_1)
            company.address_line_2 = request.POST.get('address_line_2', company.address_line_2)
            company.city = request.POST.get('city', company.city)
            company.state = request.POST.get('state', company.state)
            company.postal_code = request.POST.get('postal_code', company.postal_code)
            company.country = request.POST.get('country', company.country)
            company.phone_number = request.POST.get('phone_number', company.phone_number)
            company.email = request.POST.get('email', company.email)
            company.website = request.POST.get('website', company.website)
            company.base_currency = request.POST.get('base_currency', company.base_currency)

            # Handle financial year start date
            financial_year_start = request.POST.get('financial_year_start')
            if financial_year_start:
                company.financial_year_start = datetime.strptime(financial_year_start, '%Y-%m-%d').date()

            company.save()
            messages.success(request, 'Company profile updated successfully!')
        else:
            # Create new profile
            financial_year_start = request.POST.get('financial_year_start')
            if financial_year_start:
                financial_year_start = datetime.strptime(financial_year_start, '%Y-%m-%d').date()
            else:
                financial_year_start = timezone.now().date().replace(month=4, day=1)  # Default to April 1st

            company = CompanyProfile.objects.create(
                name=request.POST.get('name', ''),
                legal_name=request.POST.get('legal_name', ''),
                registration_number=request.POST.get('registration_number', ''),
                tax_id=request.POST.get('tax_id', ''),
                address_line_1=request.POST.get('address_line_1', ''),
                address_line_2=request.POST.get('address_line_2', ''),
                city=request.POST.get('city', ''),
                state=request.POST.get('state', ''),
                postal_code=request.POST.get('postal_code', ''),
                country=request.POST.get('country', 'India'),
                phone_number=request.POST.get('phone_number', ''),
                email=request.POST.get('email', ''),
                website=request.POST.get('website', ''),
                base_currency=request.POST.get('base_currency', 'INR'),
                financial_year_start=financial_year_start,
                is_active=True
            )
            messages.success(request, 'Company profile created successfully!')

        return redirect('core:company_profile')

    context = {
        'company': company,
    }

    return render(request, 'core/company_profile.html', context)


@login_required
def branch_management(request):
    """Manage branches."""
    from .models import Branch

    branches = Branch.objects.all().order_by('name')

    context = {
        'branches': branches,
    }

    return render(request, 'core/branch_management.html', context)


@login_required
def loan_categories(request):
    """Manage loan categories."""
    from .models import LoanCategory

    categories = LoanCategory.objects.all().order_by('name')

    context = {
        'categories': categories,
    }

    return render(request, 'core/loan_categories.html', context)


@login_required
def penalty_configurations(request):
    """Manage penalty configurations."""
    from .models import PenaltyConfiguration

    penalties = PenaltyConfiguration.objects.all().order_by('name')

    context = {
        'penalties': penalties,
    }

    return render(request, 'core/penalty_configurations.html', context)


@login_required
def test_dropdown(request):
    """Test dropdown functionality."""
    return render(request, 'test_dropdown.html')
