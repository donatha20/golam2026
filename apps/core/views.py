"""
Core views for the microfinance system.
"""
from django.shortcuts import render, redirect, get_object_or_404
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


# ============== NEW SETTINGS VIEWS ==============

@login_required
def update_company_info(request):
    """Update company information form."""
    # This redirects to the same view as company_profile but with edit mode
    return company_profile(request)


@login_required
def working_mode_settings(request):
    """Manage working mode settings."""
    from .models import WorkingMode

    working_mode = WorkingMode.get_active_mode()

    if request.method == 'POST':
        if working_mode:
            # Update existing working mode
            working_mode.name = request.POST.get('name', working_mode.name)
            working_mode.monday_enabled = 'monday_enabled' in request.POST
            working_mode.tuesday_enabled = 'tuesday_enabled' in request.POST
            working_mode.wednesday_enabled = 'wednesday_enabled' in request.POST
            working_mode.thursday_enabled = 'thursday_enabled' in request.POST
            working_mode.friday_enabled = 'friday_enabled' in request.POST
            working_mode.saturday_enabled = 'saturday_enabled' in request.POST
            working_mode.sunday_enabled = 'sunday_enabled' in request.POST
            
            working_mode.start_time = request.POST.get('start_time', working_mode.start_time)
            working_mode.end_time = request.POST.get('end_time', working_mode.end_time)
            working_mode.lunch_start = request.POST.get('lunch_start', working_mode.lunch_start)
            working_mode.lunch_end = request.POST.get('lunch_end', working_mode.lunch_end)
            
            working_mode.timezone = request.POST.get('timezone', working_mode.timezone)
            working_mode.allow_backdating = 'allow_backdating' in request.POST
            
            working_mode.save()
            messages.success(request, 'Working mode updated successfully!')
        else:
            # Create new working mode
            working_mode = WorkingMode.objects.create(
                name=request.POST.get('name', 'Default Working Mode'),
                monday_enabled='monday_enabled' in request.POST,
                tuesday_enabled='tuesday_enabled' in request.POST,
                wednesday_enabled='wednesday_enabled' in request.POST,
                thursday_enabled='thursday_enabled' in request.POST,
                friday_enabled='friday_enabled' in request.POST,
                saturday_enabled='saturday_enabled' in request.POST,
                sunday_enabled='sunday_enabled' in request.POST,
                start_time=request.POST.get('start_time', '08:00:00'),
                end_time=request.POST.get('end_time', '17:00:00'),
                lunch_start=request.POST.get('lunch_start', '12:00:00'),
                lunch_end=request.POST.get('lunch_end', '13:00:00'),
                timezone=request.POST.get('timezone', 'Africa/Dar_es_Salaam'),
                allow_backdating='allow_backdating' in request.POST,
                is_active=True
            )
            messages.success(request, 'Working mode created successfully!')

        return redirect('core:working_mode_settings')

    context = {
        'working_mode': working_mode,
        'timezone_choices': WorkingMode.TIMEZONE_CHOICES,
    }

    return render(request, 'core/working_mode_settings.html', context)


@login_required
def view_working_mode(request):
    """View current working mode settings."""
    from .models import WorkingMode

    working_mode = WorkingMode.get_active_mode()

    context = {
        'working_mode': working_mode,
    }

    return render(request, 'core/view_working_mode.html', context)


@login_required
def view_working_modes(request):
    """View all working modes."""
    from .models import WorkingMode

    working_modes = WorkingMode.objects.filter(is_active=True).order_by('name')

    context = {
        'working_modes': working_modes,
        'title': 'Working Modes',
    }

    return render(request, 'core/view_working_modes.html', context)


@login_required
def add_holiday(request):
    """Add new public holiday."""
    from .models import PublicHoliday

    if request.method == 'POST':
        name = request.POST.get('name')
        date = request.POST.get('date')
        description = request.POST.get('description', '')
        is_recurring = 'is_recurring' in request.POST

        holiday = PublicHoliday.objects.create(
            name=name,
            date=date,
            description=description,
            is_recurring=is_recurring
        )

        messages.success(request, f'Holiday "{holiday.name}" added successfully!')
        return redirect('core:view_holidays')

    context = {
        'title': 'Add Public Holiday',
    }

    return render(request, 'core/add_holiday.html', context)


@login_required
def view_holidays(request):
    """View all public holidays."""
    from .models import PublicHoliday

    holidays = PublicHoliday.objects.filter(is_active=True).order_by('date')

    context = {
        'holidays': holidays,
        'title': 'Public Holidays',
    }

    return render(request, 'core/view_holidays.html', context)


@login_required
def edit_holiday(request, holiday_id):
    """Edit existing holiday."""
    from .models import PublicHoliday
    
    holiday = get_object_or_404(PublicHoliday, id=holiday_id)

    if request.method == 'POST':
        holiday.name = request.POST.get('name', holiday.name)
        holiday.date = request.POST.get('date', holiday.date)
        holiday.description = request.POST.get('description', holiday.description)
        holiday.is_recurring = 'is_recurring' in request.POST
        holiday.save()

        messages.success(request, f'Holiday "{holiday.name}" updated successfully!')
        return redirect('core:view_holidays')

    context = {
        'holiday': holiday,
        'title': 'Edit Holiday',
    }

    return render(request, 'core/edit_holiday.html', context)


@login_required
def delete_holiday(request, holiday_id):
    """Delete holiday."""
    from .models import PublicHoliday
    
    holiday = get_object_or_404(PublicHoliday, id=holiday_id)
    
    if request.method == 'POST':
        holiday.delete()
        messages.success(request, f'Holiday "{holiday.name}" deleted successfully!')
        return redirect('core:view_holidays')

    context = {
        'holiday': holiday,
        'title': 'Delete Holiday',
    }

    return render(request, 'core/delete_holiday.html', context)


# ============== BRANCH VIEWS ==============

@login_required
def add_branch(request):
    """Add new branch."""
    from .models import Branch

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        address = request.POST.get('address', '')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')

        branch = Branch.objects.create(
            name=name,
            code=code,
            address=address,
            phone=phone,
            email=email
        )

        messages.success(request, f'Branch "{branch.name}" added successfully!')
        return redirect('core:view_branches')

    context = {
        'title': 'Add Branch',
    }

    return render(request, 'core/add_branch.html', context)


@login_required
def view_branches(request):
    """View all branches."""
    from .models import Branch

    branches = Branch.objects.filter(is_active=True).order_by('name')

    context = {
        'branches': branches,
        'title': 'Branches',
    }

    return render(request, 'core/view_branches.html', context)


@login_required
def edit_branch(request, branch_id):
    """Edit existing branch."""
    from .models import Branch
    
    branch = get_object_or_404(Branch, id=branch_id)

    if request.method == 'POST':
        branch.name = request.POST.get('name', branch.name)
        branch.code = request.POST.get('code', branch.code)
        branch.address = request.POST.get('address', branch.address)
        branch.phone = request.POST.get('phone', branch.phone)
        branch.email = request.POST.get('email', branch.email)
        branch.save()

        messages.success(request, f'Branch "{branch.name}" updated successfully!')
        return redirect('core:view_branches')

    context = {
        'branch': branch,
        'title': 'Edit Branch',
    }

    return render(request, 'core/edit_branch.html', context)


@login_required
def delete_branch(request, branch_id):
    """Delete branch."""
    from .models import Branch
    
    branch = get_object_or_404(Branch, id=branch_id)
    
    if request.method == 'POST':
        branch.is_active = False
        branch.save()
        messages.success(request, f'Branch "{branch.name}" deactivated successfully!')
        return redirect('core:view_branches')

    context = {
        'branch': branch,
        'title': 'Delete Branch',
    }

    return render(request, 'core/delete_branch.html', context)


# ============== LOAN CATEGORY VIEWS ==============

@login_required
def add_loan_category(request):
    """Add new loan category."""
    from .models import LoanCategory

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        default_interest_rate = request.POST.get('default_interest_rate')
        min_interest_rate = request.POST.get('min_interest_rate')
        max_interest_rate = request.POST.get('max_interest_rate')
        min_loan_amount = request.POST.get('min_loan_amount')
        max_loan_amount = request.POST.get('max_loan_amount')
        min_term_months = request.POST.get('min_term_months')
        max_term_months = request.POST.get('max_term_months')

        category = LoanCategory.objects.create(
            name=name,
            code=code,
            description=description,
            default_interest_rate=default_interest_rate,
            min_interest_rate=min_interest_rate,
            max_interest_rate=max_interest_rate,
            min_loan_amount=min_loan_amount,
            max_loan_amount=max_loan_amount,
            min_term_months=min_term_months,
            max_term_months=max_term_months
        )

        messages.success(request, f'Loan category "{category.name}" added successfully!')
        return redirect('core:view_loan_categories')

    context = {
        'title': 'Add Loan Category',
    }

    return render(request, 'core/add_loan_category.html', context)


@login_required
def view_loan_categories(request):
    """View all loan categories."""
    from .models import LoanCategory

    categories = LoanCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'categories': categories,
        'title': 'Loan Categories',
    }

    return render(request, 'core/view_loan_categories.html', context)


@login_required
def edit_loan_category(request, category_id):
    """Edit existing loan category."""
    from .models import LoanCategory
    
    category = get_object_or_404(LoanCategory, id=category_id)

    if request.method == 'POST':
        category.name = request.POST.get('name', category.name)
        category.code = request.POST.get('code', category.code)
        category.description = request.POST.get('description', category.description)
        category.default_interest_rate = request.POST.get('default_interest_rate', category.default_interest_rate)
        category.min_interest_rate = request.POST.get('min_interest_rate', category.min_interest_rate)
        category.max_interest_rate = request.POST.get('max_interest_rate', category.max_interest_rate)
        category.min_loan_amount = request.POST.get('min_loan_amount', category.min_loan_amount)
        category.max_loan_amount = request.POST.get('max_loan_amount', category.max_loan_amount)
        category.min_term_months = request.POST.get('min_term_months', category.min_term_months)
        category.max_term_months = request.POST.get('max_term_months', category.max_term_months)
        category.save()

        messages.success(request, f'Loan category "{category.name}" updated successfully!')
        return redirect('core:view_loan_categories')

    context = {
        'category': category,
        'title': 'Edit Loan Category',
    }

    return render(request, 'core/edit_loan_category.html', context)


@login_required
def delete_loan_category(request, category_id):
    """Delete loan category."""
    from .models import LoanCategory
    
    category = get_object_or_404(LoanCategory, id=category_id)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Loan category "{category.name}" deactivated successfully!')
        return redirect('core:view_loan_categories')

    context = {
        'category': category,
        'title': 'Delete Loan Category',
    }

    return render(request, 'core/delete_loan_category.html', context)


# ============== LOAN SECTOR VIEWS ==============

@login_required
def add_loan_sector(request):
    """Add new loan sector."""
    from .models import LoanSector

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        risk_level = request.POST.get('risk_level', 'medium')

        sector = LoanSector.objects.create(
            name=name,
            code=code,
            description=description,
            risk_level=risk_level
        )

        messages.success(request, f'Loan sector "{sector.name}" added successfully!')
        return redirect('core:view_loan_sectors')

    context = {
        'title': 'Add Loan Sector',
        'risk_levels': LoanSector._meta.get_field('risk_level').choices,
    }

    return render(request, 'core/add_loan_sector.html', context)


@login_required
def view_loan_sectors(request):
    """View all loan sectors."""
    from .models import LoanSector

    sectors = LoanSector.objects.filter(is_active=True).order_by('name')

    context = {
        'sectors': sectors,
        'title': 'Loan Sectors',
    }

    return render(request, 'core/view_loan_sectors.html', context)


@login_required
def edit_loan_sector(request, sector_id):
    """Edit existing loan sector."""
    from .models import LoanSector
    
    sector = get_object_or_404(LoanSector, id=sector_id)

    if request.method == 'POST':
        sector.name = request.POST.get('name', sector.name)
        sector.code = request.POST.get('code', sector.code)
        sector.description = request.POST.get('description', sector.description)
        sector.risk_level = request.POST.get('risk_level', sector.risk_level)
        sector.save()

        messages.success(request, f'Loan sector "{sector.name}" updated successfully!')
        return redirect('core:view_loan_sectors')

    context = {
        'sector': sector,
        'title': 'Edit Loan Sector',
        'risk_levels': LoanSector._meta.get_field('risk_level').choices,
    }

    return render(request, 'core/edit_loan_sector.html', context)


@login_required
def delete_loan_sector(request, sector_id):
    """Delete loan sector."""
    from .models import LoanSector
    
    sector = get_object_or_404(LoanSector, id=sector_id)
    
    if request.method == 'POST':
        sector.is_active = False
        sector.save()
        messages.success(request, f'Loan sector "{sector.name}" deactivated successfully!')
        return redirect('core:view_loan_sectors')

    context = {
        'sector': sector,
        'title': 'Delete Loan Sector',
    }

    return render(request, 'core/delete_loan_sector.html', context)


# ============== PENALTY CONFIGURATION VIEWS ==============

@login_required
def add_penalty_configuration(request):
    """Add new penalty configuration."""
    from .models import PenaltyConfiguration

    if request.method == 'POST':
        name = request.POST.get('name')
        penalty_type = request.POST.get('penalty_type')
        percentage_rate = request.POST.get('percentage_rate', 0)
        fixed_amount = request.POST.get('fixed_amount', 0)
        daily_rate = request.POST.get('daily_rate', 0)
        grace_period_days = request.POST.get('grace_period_days', 0)

        penalty = PenaltyConfiguration.objects.create(
            name=name,
            penalty_type=penalty_type,
            percentage_rate=percentage_rate,
            fixed_amount=fixed_amount,
            daily_rate=daily_rate,
            grace_period_days=grace_period_days
        )

        messages.success(request, f'Penalty configuration "{penalty.name}" added successfully!')
        return redirect('core:view_penalty_configurations')

    context = {
        'title': 'Add Penalty Configuration',
        'penalty_types': PenaltyConfiguration.PENALTY_TYPES,
    }

    return render(request, 'core/add_penalty_configuration.html', context)


@login_required
def add_penalty_setting(request):
    """Add new penalty setting (alias for penalty configuration)."""
    return add_penalty_configuration(request)


@login_required
def add_working_mode(request):
    """Add new working mode."""
    from .models import WorkingMode

    if request.method == 'POST':
        name = request.POST.get('name', 'Working Mode')
        monday_enabled = 'monday_enabled' in request.POST
        tuesday_enabled = 'tuesday_enabled' in request.POST
        wednesday_enabled = 'wednesday_enabled' in request.POST
        thursday_enabled = 'thursday_enabled' in request.POST
        friday_enabled = 'friday_enabled' in request.POST
        saturday_enabled = 'saturday_enabled' in request.POST
        sunday_enabled = 'sunday_enabled' in request.POST
        start_time = request.POST.get('start_time', '08:00:00')
        end_time = request.POST.get('end_time', '17:00:00')
        lunch_start = request.POST.get('lunch_start', '12:00:00')
        lunch_end = request.POST.get('lunch_end', '13:00:00')
        timezone = request.POST.get('timezone', 'Africa/Dar_es_Salaam')
        allow_backdating = 'allow_backdating' in request.POST

        mode = WorkingMode.objects.create(
            name=name,
            monday_enabled=monday_enabled,
            tuesday_enabled=tuesday_enabled,
            wednesday_enabled=wednesday_enabled,
            thursday_enabled=thursday_enabled,
            friday_enabled=friday_enabled,
            saturday_enabled=saturday_enabled,
            sunday_enabled=sunday_enabled,
            start_time=start_time,
            end_time=end_time,
            lunch_start=lunch_start,
            lunch_end=lunch_end,
            timezone=timezone,
            allow_backdating=allow_backdating
        )

        messages.success(request, f'Working mode "{mode.name}" added successfully!')
        return redirect('core:view_working_modes')

    context = {
        'title': 'Add Working Mode',
        'timezone_choices': WorkingMode.TIMEZONE_CHOICES,
    }

    return render(request, 'core/add_working_mode.html', context)


@login_required
def edit_working_mode(request, mode_id):
    """Edit existing working mode."""
    from .models import WorkingMode
    
    mode = get_object_or_404(WorkingMode, id=mode_id)

    if request.method == 'POST':
        mode.name = request.POST.get('name', mode.name)
        mode.monday_enabled = 'monday_enabled' in request.POST
        mode.tuesday_enabled = 'tuesday_enabled' in request.POST
        mode.wednesday_enabled = 'wednesday_enabled' in request.POST
        mode.thursday_enabled = 'thursday_enabled' in request.POST
        mode.friday_enabled = 'friday_enabled' in request.POST
        mode.saturday_enabled = 'saturday_enabled' in request.POST
        mode.sunday_enabled = 'sunday_enabled' in request.POST
        mode.start_time = request.POST.get('start_time', mode.start_time)
        mode.end_time = request.POST.get('end_time', mode.end_time)
        mode.lunch_start = request.POST.get('lunch_start', mode.lunch_start)
        mode.lunch_end = request.POST.get('lunch_end', mode.lunch_end)
        mode.timezone = request.POST.get('timezone', mode.timezone)
        mode.allow_backdating = 'allow_backdating' in request.POST
        
        mode.save()

        messages.success(request, f'Working mode "{mode.name}" updated successfully!')
        return redirect('core:view_working_modes')

    context = {
        'mode': mode,
        'title': 'Edit Working Mode',
        'timezone_choices': WorkingMode.TIMEZONE_CHOICES,
    }

    return render(request, 'core/edit_working_mode.html', context)


@login_required
def delete_working_mode(request, mode_id):
    """Delete working mode."""
    from .models import WorkingMode
    
    mode = get_object_or_404(WorkingMode, id=mode_id)
    
    if request.method == 'POST':
        mode.is_active = False
        mode.save()
        messages.success(request, f'Working mode "{mode.name}" deactivated successfully!')
        return redirect('core:view_working_modes')

    context = {
        'mode': mode,
        'title': 'Delete Working Mode',
    }

    return render(request, 'core/delete_working_mode.html', context)


@login_required
def view_penalty_configurations(request):
    """View all penalty configurations."""
    from .models import PenaltyConfiguration

    penalties = PenaltyConfiguration.objects.filter(is_active=True).order_by('name')

    context = {
        'penalties': penalties,
        'title': 'Penalty Configurations',
    }

    return render(request, 'core/view_penalty_configurations.html', context)


@login_required
def view_penalty_settings(request):
    """View all penalty settings."""
    from .models import PenaltyConfiguration

    penalty_settings = PenaltyConfiguration.objects.filter(is_active=True).order_by('name')

    context = {
        'penalty_settings': penalty_settings,
        'title': 'Penalty Settings',
    }

    return render(request, 'core/view_penalty_settings.html', context)


@login_required
def edit_penalty_configuration(request, penalty_id):
    """Edit existing penalty configuration."""
    from .models import PenaltyConfiguration
    
    penalty = get_object_or_404(PenaltyConfiguration, id=penalty_id)

    if request.method == 'POST':
        penalty.name = request.POST.get('name', penalty.name)
        penalty.penalty_type = request.POST.get('penalty_type', penalty.penalty_type)
        penalty.percentage_rate = request.POST.get('percentage_rate', penalty.percentage_rate)
        penalty.fixed_amount = request.POST.get('fixed_amount', penalty.fixed_amount)
        penalty.daily_rate = request.POST.get('daily_rate', penalty.daily_rate)
        penalty.grace_period_days = request.POST.get('grace_period_days', penalty.grace_period_days)
        penalty.save()

        messages.success(request, f'Penalty configuration "{penalty.name}" updated successfully!')
        return redirect('core:view_penalty_configurations')

    context = {
        'penalty': penalty,
        'title': 'Edit Penalty Configuration',
        'penalty_types': PenaltyConfiguration.PENALTY_TYPES,
    }

    return render(request, 'core/edit_penalty_configuration.html', context)


@login_required
def delete_penalty_configuration(request, penalty_id):
    """Delete penalty configuration."""
    from .models import PenaltyConfiguration
    
    penalty = get_object_or_404(PenaltyConfiguration, id=penalty_id)
    
    if request.method == 'POST':
        penalty.is_active = False
        penalty.save()
        messages.success(request, f'Penalty configuration "{penalty.name}" deactivated successfully!')
        return redirect('core:view_penalty_configurations')

    context = {
        'penalty': penalty,
        'title': 'Delete Penalty Configuration',
    }

    return render(request, 'core/delete_penalty_configuration.html', context)


# ============== INCOME SOURCE VIEWS ==============

@login_required
def add_income_source(request):
    """Add new income source."""
    from .models import IncomeSource

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        source_type = request.POST.get('source_type', 'operational')

        source = IncomeSource.objects.create(
            name=name,
            code=code,
            description=description,
            source_type=source_type
        )

        messages.success(request, f'Income source "{source.name}" added successfully!')
        return redirect('core:view_income_sources')

    context = {
        'title': 'Add Income Source',
        'source_types': IncomeSource._meta.get_field('source_type').choices,
    }

    return render(request, 'core/add_income_source.html', context)


@login_required
def view_income_sources(request):
    """View all income sources."""
    from .models import IncomeSource

    income_sources = IncomeSource.objects.filter(is_active=True).order_by('name')

    context = {
        'income_sources': income_sources,
        'title': 'Income Sources',
    }

    return render(request, 'core/view_income_sources.html', context)


@login_required
def edit_income_source(request, source_id):
    """Edit existing income source."""
    from .models import IncomeSource
    
    source = get_object_or_404(IncomeSource, id=source_id)

    if request.method == 'POST':
        source.name = request.POST.get('name', source.name)
        source.code = request.POST.get('code', source.code)
        source.description = request.POST.get('description', source.description)
        source.source_type = request.POST.get('source_type', source.source_type)
        source.save()

        messages.success(request, f'Income source "{source.name}" updated successfully!')
        return redirect('core:view_income_sources')

    context = {
        'source': source,
        'title': 'Edit Income Source',
        'source_types': IncomeSource._meta.get_field('source_type').choices,
    }

    return render(request, 'core/edit_income_source.html', context)


@login_required
def delete_income_source(request, source_id):
    """Delete income source."""
    from .models import IncomeSource
    
    source = get_object_or_404(IncomeSource, id=source_id)
    
    if request.method == 'POST':
        source.is_active = False
        source.save()
        messages.success(request, f'Income source "{source.name}" deactivated successfully!')
        return redirect('core:view_income_sources')

    context = {
        'source': source,
        'title': 'Delete Income Source',
    }

    return render(request, 'core/delete_income_source.html', context)


# ============== EXPENSE CATEGORY VIEWS ==============

@login_required
def add_expense_category(request):
    """Add new expense category."""
    from .models import ExpenseCategory

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        category_type = request.POST.get('category_type', 'operational')

        category = ExpenseCategory.objects.create(
            name=name,
            code=code,
            description=description,
            category_type=category_type
        )

        messages.success(request, f'Expense category "{category.name}" added successfully!')
        return redirect('core:view_expense_categories')

    context = {
        'title': 'Add Expense Category',
        'category_types': ExpenseCategory._meta.get_field('category_type').choices,
    }

    return render(request, 'core/add_expense_category.html', context)


@login_required
def view_expense_categories(request):
    """View all expense categories."""
    from .models import ExpenseCategory

    expense_categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'expense_categories': expense_categories,
        'title': 'Expense Categories',
    }

    return render(request, 'core/view_expense_categories.html', context)


@login_required
def edit_expense_category(request, category_id):
    """Edit existing expense category."""
    from .models import ExpenseCategory
    
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        category.name = request.POST.get('name', category.name)
        category.code = request.POST.get('code', category.code)
        category.description = request.POST.get('description', category.description)
        category.category_type = request.POST.get('category_type', category.category_type)
        category.save()

        messages.success(request, f'Expense category "{category.name}" updated successfully!')
        return redirect('core:view_expense_categories')

    context = {
        'category': category,
        'title': 'Edit Expense Category',
        'category_types': ExpenseCategory._meta.get_field('category_type').choices,
    }

    return render(request, 'core/edit_expense_category.html', context)


@login_required
def delete_expense_category(request, category_id):
    """Delete expense category."""
    from .models import ExpenseCategory
    
    category = get_object_or_404(ExpenseCategory, id=category_id)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Expense category "{category.name}" deactivated successfully!')
        return redirect('core:view_expense_categories')

    context = {
        'category': category,
        'title': 'Delete Expense Category',
    }

    return render(request, 'core/delete_expense_category.html', context)


# ============== ASSET CATEGORY VIEWS ==============

@login_required
def add_asset_category(request):
    """Add new asset category."""
    from .models import AssetCategory

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        depreciation_method = request.POST.get('depreciation_method', 'straight_line')
        depreciation_rate = request.POST.get('depreciation_rate', 10.0)
        useful_life_years = request.POST.get('useful_life_years', 5)

        category = AssetCategory.objects.create(
            name=name,
            code=code,
            description=description,
            depreciation_method=depreciation_method,
            depreciation_rate=depreciation_rate,
            useful_life_years=useful_life_years
        )

        messages.success(request, f'Asset category "{category.name}" added successfully!')
        return redirect('core:view_asset_categories')

    context = {
        'title': 'Add Asset Category',
        'depreciation_methods': AssetCategory._meta.get_field('depreciation_method').choices,
    }

    return render(request, 'core/add_asset_category.html', context)


@login_required
def view_asset_categories(request):
    """View all asset categories."""
    from .models import AssetCategory

    asset_categories = AssetCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'asset_categories': asset_categories,
        'title': 'Asset Categories',
    }

    return render(request, 'core/view_asset_categories.html', context)


@login_required
def edit_asset_category(request, category_id):
    """Edit existing asset category."""
    from .models import AssetCategory
    
    category = get_object_or_404(AssetCategory, id=category_id)

    if request.method == 'POST':
        category.name = request.POST.get('name', category.name)
        category.code = request.POST.get('code', category.code)
        category.description = request.POST.get('description', category.description)
        category.depreciation_method = request.POST.get('depreciation_method', category.depreciation_method)
        category.depreciation_rate = request.POST.get('depreciation_rate', category.depreciation_rate)
        category.useful_life_years = request.POST.get('useful_life_years', category.useful_life_years)
        category.save()

        messages.success(request, f'Asset category "{category.name}" updated successfully!')
        return redirect('core:view_asset_categories')

    context = {
        'category': category,
        'title': 'Edit Asset Category',
        'depreciation_methods': AssetCategory._meta.get_field('depreciation_method').choices,
    }

    return render(request, 'core/edit_asset_category.html', context)


@login_required
def delete_asset_category(request, category_id):
    """Delete asset category."""
    from .models import AssetCategory
    
    category = get_object_or_404(AssetCategory, id=category_id)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Asset category "{category.name}" deactivated successfully!')
        return redirect('core:view_asset_categories')

    context = {
        'category': category,
        'title': 'Delete Asset Category',
    }

    return render(request, 'core/delete_asset_category.html', context)


# ============== BANK ACCOUNT VIEWS ==============

@login_required
def add_bank_account(request):
    """Add new bank account."""
    from .models import BankAccount

    if request.method == 'POST':
        name = request.POST.get('name')
        account_number = request.POST.get('account_number')
        account_type = request.POST.get('account_type')
        bank_name = request.POST.get('bank_name', '')
        bank_branch = request.POST.get('bank_branch', '')
        opening_balance = request.POST.get('opening_balance', 0)

        account = BankAccount.objects.create(
            name=name,
            account_number=account_number,
            account_type=account_type,
            bank_name=bank_name,
            bank_branch=bank_branch,
            opening_balance=opening_balance,
            current_balance=opening_balance
        )

        messages.success(request, f'Bank account "{account.name}" added successfully!')
        return redirect('core:view_bank_accounts')

    context = {
        'title': 'Add Bank Account',
        'account_types': BankAccount.ACCOUNT_TYPES,
    }

    return render(request, 'core/add_bank_account.html', context)


@login_required
def view_bank_accounts(request):
    """View all bank accounts."""
    from .models import BankAccount

    bank_accounts = BankAccount.objects.filter(is_active=True).order_by('-is_default', 'name')

    context = {
        'bank_accounts': bank_accounts,
        'title': 'Bank Accounts',
    }

    return render(request, 'core/view_bank_accounts.html', context)


@login_required
def edit_bank_account(request, account_id):
    """Edit existing bank account."""
    from .models import BankAccount
    
    account = get_object_or_404(BankAccount, id=account_id)

    if request.method == 'POST':
        account.name = request.POST.get('name', account.name)
        account.account_number = request.POST.get('account_number', account.account_number)
        account.account_type = request.POST.get('account_type', account.account_type)
        account.bank_name = request.POST.get('bank_name', account.bank_name)
        account.bank_branch = request.POST.get('bank_branch', account.bank_branch)
        account.is_default = 'is_default' in request.POST
        account.save()

        messages.success(request, f'Bank account "{account.name}" updated successfully!')
        return redirect('core:view_bank_accounts')

    context = {
        'account': account,
        'title': 'Edit Bank Account',
        'account_types': BankAccount.ACCOUNT_TYPES,
    }

    return render(request, 'core/edit_bank_account.html', context)


@login_required
def delete_bank_account(request, account_id):
    """Delete bank account."""
    from .models import BankAccount
    
    account = get_object_or_404(BankAccount, id=account_id)
    
    if request.method == 'POST':
        account.is_active = False
        account.save()
        messages.success(request, f'Bank account "{account.name}" deactivated successfully!')
        return redirect('core:view_bank_accounts')

    context = {
        'account': account,
        'title': 'Delete Bank Account',
    }

    return render(request, 'core/delete_bank_account.html', context)


@login_required
def test_dropdown(request):
    """Test dropdown functionality."""
    return render(request, 'test_dropdown.html')
