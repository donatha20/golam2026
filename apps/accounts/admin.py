"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Branch, UserSession, UserActivity


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Custom user admin configuration."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'branch', 'is_active')
    list_filter = ('role', 'branch', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'employee_id')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'employee_id', 'phone_number', 'branch', 'profile_picture', 
                      'date_of_birth', 'address', 'emergency_contact_name', 'emergency_contact_phone', 
                      'hire_date')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'employee_id', 'phone_number', 'branch')
        }),
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """Branch admin configuration."""
    list_display = ('name', 'code', 'manager', 'phone_number', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'address')
    ordering = ('name',)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """User session admin configuration."""
    list_display = ('user', 'ip_address', 'login_time', 'logout_time', 'is_active')
    list_filter = ('is_active', 'login_time')
    search_fields = ('user__username', 'ip_address')
    ordering = ('-login_time',)
    readonly_fields = ('session_key', 'user_agent', 'login_time')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User activity admin configuration."""
    list_display = ('user', 'action', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action', 'description')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)
