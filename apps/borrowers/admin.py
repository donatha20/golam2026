"""
Admin configuration for borrowers app.
"""
from django.contrib import admin
from .models import Borrower, BorrowerDocument, BorrowerGroup, GroupMembership


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    """Admin configuration for Borrower model."""
    list_display = (
        'borrower_id', 'get_full_name', 'phone_number', 'gender', 
        'age', 'status', 'branch', 'registration_date'
    )
    list_filter = (
        'status', 'gender', 'marital_status', 'branch', 
        'registration_date', 'created_at'
    )
    search_fields = (
        'borrower_id', 'first_name', 'last_name', 'phone_number', 
        'email', 'id_number'
    )
    readonly_fields = ('borrower_id', 'created_at', 'updated_at')
    ordering = ('-registration_date',)
    
    fieldsets = (
        ('System Information', {
            'fields': ('borrower_id', 'status', 'registration_date', 'branch', 'registered_by')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'last_name', 'middle_name', 'gender', 
                'date_of_birth', 'marital_status', 'occupation'
            )
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email', 'photo')
        }),
        ('Identification', {
            'fields': ('id_type', 'id_number', 'id_issue_date', 'id_expiry_date')
        }),
        ('Address', {
            'fields': ('house_number', 'street', 'ward', 'district', 'region')
        }),
        ('Next of Kin', {
            'fields': (
                'next_of_kin_name', 'next_of_kin_relationship', 
                'next_of_kin_phone', 'next_of_kin_address'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """Return the full name of the borrower."""
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    def age(self, obj):
        """Return the age of the borrower."""
        return obj.age
    age.short_description = 'Age'


@admin.register(BorrowerDocument)
class BorrowerDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for BorrowerDocument model."""
    list_display = (
        'borrower', 'document_type', 'document_name', 
        'is_verified', 'verified_by', 'created_at'
    )
    list_filter = (
        'document_type', 'is_verified', 'verification_date', 'created_at'
    )
    search_fields = (
        'borrower__first_name', 'borrower__last_name', 
        'document_name', 'document_type'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Document Information', {
            'fields': ('borrower', 'document_type', 'document_name', 'document_file', 'description')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verification_date')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BorrowerGroup)
class BorrowerGroupAdmin(admin.ModelAdmin):
    """Admin configuration for BorrowerGroup model."""
    list_display = (
        'group_id', 'group_name', 'group_leader', 'member_count', 
        'status', 'formation_date', 'branch'
    )
    list_filter = (
        'status', 'meeting_frequency', 'branch', 'formation_date', 'created_at'
    )
    search_fields = (
        'group_id', 'group_name', 'group_leader__first_name', 
        'group_leader__last_name'
    )
    readonly_fields = ('group_id', 'created_at', 'updated_at')
    ordering = ('-formation_date',)
    
    fieldsets = (
        ('Group Information', {
            'fields': (
                'group_id', 'group_name', 'description', 'group_leader', 
                'formation_date', 'branch', 'registered_by'
            )
        }),
        ('Group Settings', {
            'fields': (
                'minimum_members', 'maximum_members', 'meeting_frequency', 
                'meeting_day', 'status'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        """Return the number of members in the group."""
        return obj.member_count
    member_count.short_description = 'Members'


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for GroupMembership model."""
    list_display = (
        'group', 'borrower', 'role', 'join_date', 
        'leave_date', 'is_active'
    )
    list_filter = (
        'role', 'is_active', 'join_date', 'leave_date'
    )
    search_fields = (
        'group__group_name', 'borrower__first_name', 'borrower__last_name'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Membership Information', {
            'fields': ('group', 'borrower', 'role', 'join_date', 'leave_date', 'is_active')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
