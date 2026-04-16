"""
Views for borrower/client management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django_tables2 import RequestConfig
from datetime import datetime, timedelta

from .models import Borrower, BorrowerGroup, GroupMembership, BorrowerStatus
from .tables import BorrowerTable, BorrowerGroupTable, RegistrationReportTable
from .forms import BorrowerRegistrationForm, BorrowerGroupForm
from apps.accounts.models import UserRole, UserActivity
from apps.core.models import Branch
from apps.loans.models import Loan


def _require_elevated_access(request):
    """Restrict destructive borrower actions to admin/manager users."""
    role = getattr(request.user, 'role', None)
    if role in {UserRole.ADMIN, UserRole.MANAGER}:
        return None
    if any([
        getattr(request.user, 'is_admin', False),
        getattr(request.user, 'is_staff', False),
        getattr(request.user, 'is_superuser', False),
    ]):
        return None
    messages.error(request, 'Access denied. Admin or manager privileges required.')
    return redirect('core:dashboard')


@login_required
def borrower_list(request):
    """Display list of all borrowers/clients."""
    borrowers = Borrower.objects.select_related('branch', 'registered_by').order_by('-registration_date')
    
    # Create data table
    table = BorrowerTable(borrowers)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)
    
    # Statistics
    stats = {
        'total_borrowers': borrowers.count(),
        'active_borrowers': borrowers.filter(status=BorrowerStatus.ACTIVE).count(),
        'suspended_borrowers': borrowers.filter(status=BorrowerStatus.SUSPENDED).count(),
        'new_this_month': borrowers.filter(
            registration_date__gte=timezone.now().date().replace(day=1)
        ).count(),
    }
    
    context = {
        'table': table,
        'stats': stats,
    }
    return render(request, 'borrowers/borrower_list.html', context)


@login_required
def register_borrower(request):
    """Register a new borrower/client."""
    if request.method == 'POST':
        try:
            # Get registration data
            registration_date = request.POST.get('registration_date')
            branch_id = request.POST.get('branch')

            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            middle_name = request.POST.get('middle_name', '').strip()
            nickname = request.POST.get('nickname', '').strip()
            gender = request.POST.get('gender')
            date_of_birth = request.POST.get('date_of_birth')
            marital_status = request.POST.get('marital_status')
            occupation = request.POST.get('occupation', '').strip()
            
            # Contact information
            phone_number = request.POST.get('phone_number', '').strip()
            email = request.POST.get('email', '').strip()
            
            # Identification
            id_type = request.POST.get('id_type')
            id_number = request.POST.get('id_number', '').strip()
            
            # Address
            street = request.POST.get('street', '').strip()
            ward = request.POST.get('ward', '').strip()
            district = request.POST.get('district', '').strip()
            region = request.POST.get('region', '').strip()
            
            # Next of kin
            next_of_kin_name = request.POST.get('next_of_kin_name', '').strip()
            next_of_kin_relationship = request.POST.get('next_of_kin_relationship', '').strip()
            next_of_kin_phone = request.POST.get('next_of_kin_phone', '').strip()
            next_of_kin_address = request.POST.get('next_of_kin_address', '').strip()
            
            # Get branch
            try:
                branch = Branch.objects.get(id=branch_id) if branch_id else request.user.branch
            except Branch.DoesNotExist:
                messages.error(request, 'Selected branch not found.')
                return render(request, 'borrowers/register_borrower.html', {
                    'branches': Branch.objects.filter(is_active=True),
                    'gender_choices': [('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                    'marital_choices': [
                        ('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'),
                        ('widowed', 'Widowed'), ('separated', 'Separated')
                    ],
                    'id_type_choices': [
                        ('national_id', 'National ID'), ('passport', 'Passport'),
                        ('drivers_license', "Driver's License"), ('voter_id', 'Voter ID')
                    ],
                })

            # Validation
            required_fields = [
                first_name, last_name, gender, date_of_birth, marital_status,
                occupation, phone_number, id_type, id_number, street, ward,
                district, region, next_of_kin_name, next_of_kin_relationship,
                next_of_kin_phone, next_of_kin_address, registration_date
            ]

            if not all(required_fields):
                messages.error(request, 'All required fields must be filled.')
                return render(request, 'borrowers/register_borrower.html', {
                    'branches': Branch.objects.filter(is_active=True),
                    'gender_choices': [('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                    'marital_choices': [
                        ('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'),
                        ('widowed', 'Widowed'), ('separated', 'Separated')
                    ],
                    'id_type_choices': [
                        ('national_id', 'National ID'), ('passport', 'Passport'),
                        ('drivers_license', "Driver's License"), ('voter_id', 'Voter ID')
                    ],
                })
            
            # Check for duplicate ID number
            if Borrower.objects.filter(id_number=id_number).exists():
                messages.error(request, 'A borrower with this ID number already exists.')
                return render(request, 'borrowers/register_borrower.html')
            
            # Check for duplicate phone number
            if Borrower.objects.filter(phone_number=phone_number).exists():
                messages.error(request, 'A borrower with this phone number already exists.')
                return render(request, 'borrowers/register_borrower.html')
            
            # Create borrower
            borrower = Borrower.objects.create(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name or None,
                nickname=nickname or None,
                gender=gender,
                date_of_birth=date_of_birth,
                marital_status=marital_status,
                occupation=occupation,
                phone_number=phone_number,
                email=email or None,
                id_type=id_type,
                id_number=id_number,
                street=street,
                ward=ward,
                district=district,
                region=region,
                next_of_kin_name=next_of_kin_name,
                next_of_kin_relationship=next_of_kin_relationship,
                next_of_kin_phone=next_of_kin_phone,
                next_of_kin_address=next_of_kin_address,
                registration_date=registration_date,
                branch=branch,
                registered_by=request.user,
                created_by=request.user,
            )
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='REGISTER_BORROWER',
                description=f'Registered new borrower: {borrower.get_full_name()} ({borrower.borrower_id})',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='Borrower',
                object_id=borrower.id
            )

            # Create in-app notifications for approval/elevated users.
            try:
                from apps.accounts.models import CustomUser
                from apps.notifications.models import NotificationType
                from apps.notifications.utils import create_notifications_for_users

                recipients = CustomUser.objects.filter(
                    role__in=['admin', 'manager'],
                    is_active=True,
                ).exclude(id=request.user.id)

                create_notifications_for_users(
                    recipients=recipients,
                    actor=request.user,
                    title='New Borrower Registered',
                    message=f'{borrower.get_full_name()} ({borrower.borrower_id}) was registered at {borrower.branch.name}.',
                    notification_type=NotificationType.INFO,
                    target_url=f'/borrowers/{borrower.id}/view/',
                )
            except Exception:
                # Do not block borrower registration if notifications fail.
                pass
            
            messages.success(request, f'Borrower {borrower.get_full_name()} registered successfully! ID: {borrower.borrower_id}')
            return redirect('borrowers:borrower_list')
            
        except Exception as e:
            messages.error(request, f'Error registering borrower: {str(e)}')
    
    context = {
        'branches': Branch.objects.filter(is_active=True),
        'today': timezone.now().date(),
        'gender_choices': [('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        'marital_choices': [
            ('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'),
            ('widowed', 'Widowed'), ('separated', 'Separated')
        ],
        'id_type_choices': [
            ('national_id', 'National ID'), ('passport', 'Passport'),
            ('drivers_license', "Driver's License"), ('voter_id', 'Voter ID')
        ],
    }
    return render(request, 'borrowers/register_borrower.html', context)


@login_required
def registration_report(request):
    """Display borrower registration report."""
    # Get filters from request
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    branch_id = request.GET.get('branch')
    officer_id = request.GET.get('officer')
    
    start_date = None
    end_date = None

    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.warning(request, 'Invalid start date format ignored.')

    if end_date_param:
        try:
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.warning(request, 'Invalid end date format ignored.')

    # Ensure range order is always valid when both bounds are present.
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    borrowers = Borrower.objects.select_related('branch', 'registered_by').order_by('-registration_date')

    if start_date:
        borrowers = borrowers.filter(registration_date__gte=start_date)
    if end_date:
        borrowers = borrowers.filter(registration_date__lte=end_date)
    if branch_id:
        borrowers = borrowers.filter(branch_id=branch_id)
    if officer_id:
        borrowers = borrowers.filter(registered_by_id=officer_id)
    
    # Create data table
    table = RegistrationReportTable(borrowers)
    RequestConfig(request, paginate={"per_page": 50}).configure(table)

    total_registered = borrowers.count()
    male_borrowers = borrowers.filter(gender='male').count()
    female_borrowers = borrowers.filter(gender='female').count()
    other_borrowers = max(total_registered - male_borrowers - female_borrowers, 0)

    male_percentage = round((male_borrowers / total_registered) * 100, 1) if total_registered else 0
    female_percentage = round((female_borrowers / total_registered) * 100, 1) if total_registered else 0
    other_percentage = round((other_borrowers / total_registered) * 100, 1) if total_registered else 0

    by_branch = list(
        borrowers.values('branch_id', 'branch__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    for item in by_branch:
        item['percentage'] = round((item['count'] / total_registered) * 100, 1) if total_registered else 0

    by_officer = list(
        borrowers.values('registered_by_id', 'registered_by__first_name', 'registered_by__last_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    for item in by_officer:
        item['percentage'] = round((item['count'] / total_registered) * 100, 1) if total_registered else 0
    
    # Statistics
    stats = {
        'total_registered': total_registered,
        'male_borrowers': male_borrowers,
        'female_borrowers': female_borrowers,
        'other_borrowers': other_borrowers,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'other_percentage': other_percentage,
        'by_branch': by_branch,
        'by_officer': by_officer,
    }

    branches = Branch.objects.filter(is_active=True).order_by('name')
    officers = (
        Borrower.objects.select_related('registered_by')
        .values('registered_by_id', 'registered_by__first_name', 'registered_by__last_name')
        .distinct()
        .order_by('registered_by__first_name', 'registered_by__last_name')
    )
    
    context = {
        'table': table,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'branches': branches,
        'officers': officers,
        'selected_branch_id': branch_id,
        'selected_officer_id': officer_id,
    }
    return render(request, 'borrowers/registration_report.html', context)


@login_required
def borrowers_without_loans(request):
    """Display borrowers who have never taken a loan."""
    # Get borrowers without any loans
    borrowers_without_loans = Borrower.objects.filter(
        loans__isnull=True,
        status=BorrowerStatus.ACTIVE
    ).select_related('branch', 'registered_by').order_by('-registration_date')
    
    # Create data table
    table = BorrowerTable(borrowers_without_loans)
    RequestConfig(request, paginate={"per_page": 25}).configure(table)
    
    # Statistics
    total_borrowers = Borrower.objects.filter(status=BorrowerStatus.ACTIVE).count()
    borrowers_with_loans = Borrower.objects.filter(
        loans__isnull=False,
        status=BorrowerStatus.ACTIVE
    ).distinct().count()
    
    stats = {
        'total_active_borrowers': total_borrowers,
        'borrowers_with_loans': borrowers_with_loans,
        'borrowers_without_loans': borrowers_without_loans.count(),
        'percentage_without_loans': round(
            (borrowers_without_loans.count() / total_borrowers * 100) if total_borrowers > 0 else 0, 1
        ),
    }
    
    context = {
        'table': table,
        'stats': stats,
    }
    return render(request, 'borrowers/borrowers_without_loans.html', context)


# Group Management Views
@login_required
def group_list(request):
    """Display list of all borrower groups."""
    groups = BorrowerGroup.objects.select_related('group_leader', 'branch', 'registered_by').order_by('-formation_date')

    # Create data table
    table = BorrowerGroupTable(groups)
    RequestConfig(request, paginate={"per_page": 20}).configure(table)

    # Statistics
    stats = {
        'total_groups': groups.count(),
        'active_groups': groups.filter(status='active').count(),
        'inactive_groups': groups.filter(status='inactive').count(),
        'total_members': GroupMembership.objects.filter(is_active=True).count(),
        'average_group_size': round(
            GroupMembership.objects.filter(is_active=True).count() / groups.filter(status='active').count()
            if groups.filter(status='active').count() > 0 else 0, 1
        ),
    }

    context = {
        'table': table,
        'stats': stats,
    }
    return render(request, 'borrowers/group_list.html', context)


@login_required
def register_group(request):
    """Register a new borrower group."""
    if request.method == 'POST':
        try:
            # Get registration data
            formation_date = request.POST.get('formation_date')
            branch_id = request.POST.get('branch')

            # Get form data
            group_name = request.POST.get('group_name', '').strip()
            description = request.POST.get('description', '').strip()
            group_leader_id = request.POST.get('group_leader')
            minimum_members = request.POST.get('minimum_members', 5)
            maximum_members = request.POST.get('maximum_members', 20)
            meeting_frequency = request.POST.get('meeting_frequency', 'weekly')
            meeting_day = request.POST.get('meeting_day', '')

            # Get branch
            try:
                branch = Branch.objects.get(id=branch_id) if branch_id else request.user.branch
            except Branch.DoesNotExist:
                messages.error(request, 'Selected branch not found.')
                return render(request, 'borrowers/register_group.html', {
                    'available_borrowers': get_available_borrowers(),
                    'branches': Branch.objects.filter(is_active=True),
                    'today': timezone.now().date(),
                    'meeting_frequency_choices': [
                        ('weekly', 'Weekly'), ('biweekly', 'Bi-weekly'), ('monthly', 'Monthly')
                    ],
                    'meeting_day_choices': [
                        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
                        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
                        ('sunday', 'Sunday')
                    ],
                })

            # Validation
            if not all([group_name, group_leader_id, formation_date]):
                messages.error(request, 'Group name, leader, and formation date are required.')
                return render(request, 'borrowers/register_group.html', {
                    'available_borrowers': get_available_borrowers(),
                    'branches': Branch.objects.filter(is_active=True),
                    'today': timezone.now().date(),
                    'meeting_frequency_choices': [
                        ('weekly', 'Weekly'), ('biweekly', 'Bi-weekly'), ('monthly', 'Monthly')
                    ],
                    'meeting_day_choices': [
                        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
                        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
                        ('sunday', 'Sunday')
                    ],
                })

            # Check for duplicate group name
            if BorrowerGroup.objects.filter(group_name=group_name).exists():
                messages.error(request, 'A group with this name already exists.')
                return render(request, 'borrowers/register_group.html', {
                    'available_borrowers': get_available_borrowers()
                })

            # Get group leader
            try:
                group_leader = Borrower.objects.get(id=group_leader_id, status=BorrowerStatus.ACTIVE)
            except Borrower.DoesNotExist:
                messages.error(request, 'Selected group leader not found or not active.')
                return render(request, 'borrowers/register_group.html', {
                    'available_borrowers': get_available_borrowers()
                })

            # Create group
            group = BorrowerGroup.objects.create(
                group_name=group_name,
                description=description or None,
                group_leader=group_leader,
                formation_date=formation_date,
                branch=branch,
                registered_by=request.user,
                minimum_members=int(minimum_members),
                maximum_members=int(maximum_members),
                meeting_frequency=meeting_frequency,
                meeting_day=meeting_day or None,
                created_by=request.user,
            )

            # Add group leader as a member with leader role
            GroupMembership.objects.create(
                group=group,
                borrower=group_leader,
                role='leader',
                created_by=request.user,
            )

            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='REGISTER_GROUP',
                description=f'Registered new group: {group.group_name} ({group.group_id})',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='BorrowerGroup',
                object_id=group.id
            )

            messages.success(request, f'Group {group.group_name} registered successfully! ID: {group.group_id}')
            return redirect('borrowers:group_list')

        except Exception as e:
            messages.error(request, f'Error registering group: {str(e)}')

    context = {
        'available_borrowers': get_available_borrowers(),
        'branches': Branch.objects.filter(is_active=True),
        'today': timezone.now().date(),
        'meeting_frequency_choices': [
            ('weekly', 'Weekly'), ('biweekly', 'Bi-weekly'), ('monthly', 'Monthly')
        ],
        'meeting_day_choices': [
            ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
            ('sunday', 'Sunday')
        ],
    }
    return render(request, 'borrowers/register_group.html', context)


@login_required
def borrower_detail(request, borrower_id):
    """View borrower details."""
    borrower = get_object_or_404(Borrower, id=borrower_id)

    # Get borrower's loans
    loans = borrower.loans.all().order_by('-application_date')

    # Get borrower's payments
    payments = borrower.payments.all().order_by('-payment_date')[:10]

    # Get borrower's savings accounts
    savings_accounts = borrower.savings_accounts.all()

    context = {
        'borrower': borrower,
        'loans': loans,
        'payments': payments,
        'savings_accounts': savings_accounts,
    }
    return render(request, 'borrowers/borrower_detail.html', context)


@login_required
def borrower_edit(request, borrower_id):
    """Edit borrower details."""
    borrower = get_object_or_404(Borrower, id=borrower_id)

    if request.method == 'POST':
        form = BorrowerRegistrationForm(request.POST, request.FILES, instance=borrower, user=request.user)
        if form.is_valid():
            borrower = form.save(commit=False)
            borrower.updated_by = request.user
            borrower.save()

            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='UPDATE_BORROWER',
                description=f'Updated borrower: {borrower.get_full_name()} ({borrower.borrower_id})',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='Borrower',
                object_id=borrower.id
            )

            messages.success(request, f'Borrower {borrower.get_full_name()} updated successfully!')
            return redirect('borrowers:borrower_detail', borrower_id=borrower.id)
    else:
        form = BorrowerRegistrationForm(instance=borrower, user=request.user)

    context = {
        'form': form,
        'borrower': borrower,
    }
    return render(request, 'borrowers/borrower_edit.html', context)


@login_required
def borrower_delete(request, borrower_id):
    """Deactivate a borrower record (soft delete)."""
    denied_response = _require_elevated_access(request)
    if denied_response:
        return denied_response

    borrower = get_object_or_404(Borrower, id=borrower_id)

    if request.method == 'POST':
        borrower.status = BorrowerStatus.INACTIVE
        borrower.updated_by = request.user
        borrower.save(update_fields=['status', 'updated_by', 'updated_at'])

        UserActivity.objects.create(
            user=request.user,
            action='DEACTIVATE_BORROWER',
            description=f'Deactivated borrower: {borrower.get_full_name()} ({borrower.borrower_id})',
            ip_address=request.META.get('REMOTE_ADDR', ''),
            content_type='Borrower',
            object_id=borrower.id
        )

        messages.success(request, f'Borrower {borrower.get_full_name()} deactivated successfully.')
        return redirect('borrowers:borrower_list')

    return render(request, 'borrowers/borrower_delete.html', {'borrower': borrower})


@login_required
def group_delete(request, group_id):
    """Deactivate a borrower group (soft delete)."""
    denied_response = _require_elevated_access(request)
    if denied_response:
        return denied_response

    group = get_object_or_404(BorrowerGroup, id=group_id)

    if request.method == 'POST':
        group.status = StatusChoices.INACTIVE
        group.updated_by = request.user
        group.save(update_fields=['status', 'updated_by', 'updated_at'])

        UserActivity.objects.create(
            user=request.user,
            action='DEACTIVATE_GROUP',
            description=f'Deactivated group: {group.group_name} ({group.group_id})',
            ip_address=request.META.get('REMOTE_ADDR', ''),
            content_type='BorrowerGroup',
            object_id=group.id
        )

        messages.success(request, f'Group {group.group_name} deactivated successfully.')
        return redirect('borrowers:group_list')

    return render(request, 'borrowers/group_delete.html', {'group': group})


def get_available_borrowers():
    """Get borrowers available to be group leaders or members."""
    return Borrower.objects.filter(
        status=BorrowerStatus.ACTIVE
    ).order_by('first_name', 'last_name')


