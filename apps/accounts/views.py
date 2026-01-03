"""
Views for the accounts app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import CustomUser, Branch, UserActivity, UserSession
from .forms import UserProfileForm, UserCreateForm, BranchForm


@login_required
def account_settings(request):
    """Account settings and security page."""
    # Get user sessions
    user_sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-login_time')[:10]
    
    # Get recent activities
    recent_activities = UserActivity.objects.filter(
        user=request.user
    ).order_by('-timestamp')[:20]
    
    context = {
        'user_sessions': user_sessions,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'accounts/account_settings.html', context)


@login_required
def profile_view(request):
    """User profile view."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='UPDATE_PROFILE',
                description='Updated profile information',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='CustomUser',
                object_id=request.user.id
            )
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'user': request.user
    })


@login_required
def change_password(request):
    """Change password view."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='CHANGE_PASSWORD',
                description='Changed password',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='CustomUser',
                object_id=request.user.id
            )
            
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {
        'form': form
    })


@login_required
def user_management(request):
    """User management view - admin only."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')
    
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Filter users
    users = CustomUser.objects.all()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_users': CustomUser.objects.count(),
        'active_users': CustomUser.objects.filter(is_active=True).count(),
        'inactive_users': CustomUser.objects.filter(is_active=False).count(),
    }
    
    return render(request, 'accounts/user_management.html', context)


@login_required
def create_user(request):
    """Create new user - admin only."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE_USER',
                description=f'Created new user: {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='CustomUser',
                object_id=user.id
            )
            
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('accounts:user_management')
    else:
        form = UserCreateForm()
    
    return render(request, 'accounts/create_user.html', {
        'form': form
    })


@login_required
def edit_user(request, user_id):
    """Edit user - admin only."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='UPDATE_USER',
                description=f'Updated user: {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='CustomUser',
                object_id=user.id
            )
            
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('accounts:user_management')
    else:
        form = UserProfileForm(instance=user)
    
    return render(request, 'accounts/edit_user.html', {
        'form': form,
        'user_obj': user
    })


@login_required
@require_http_methods(["POST"])
def toggle_user_status(request, user_id):
    """Toggle user active status - admin only."""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = get_object_or_404(CustomUser, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    # Log the activity
    action = 'ACTIVATE_USER' if user.is_active else 'DEACTIVATE_USER'
    UserActivity.objects.create(
        user=request.user,
        action=action,
        description=f'{"Activated" if user.is_active else "Deactivated"} user: {user.username}',
        ip_address=request.META.get('REMOTE_ADDR', ''),
        content_type='CustomUser',
        object_id=user.id
    )
    
    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully'
    })


@login_required
def branch_management(request):
    """Branch management view - admin only."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')
    
    branches = Branch.objects.all().order_by('name')
    
    return render(request, 'accounts/branch_management.html', {
        'branches': branches
    })


@login_required
def create_branch(request):
    """Create new branch - admin only."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action='CREATE_BRANCH',
                description=f'Created new branch: {branch.name}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                content_type='Branch',
                object_id=branch.id
            )
            
            messages.success(request, f'Branch {branch.name} created successfully!')
            return redirect('accounts:branch_management')
    else:
        form = BranchForm()
    
    return render(request, 'accounts/create_branch.html', {
        'form': form
    })


@login_required
def user_activity_log(request):
    """User activity log view - admin only."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('core:dashboard')
    
    activities = UserActivity.objects.select_related('user').order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/activity_log.html', {
        'page_obj': page_obj
    })
