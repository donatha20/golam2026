"""
Admin configuration for loans app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Loan, RepaymentSchedule, LoanPenalty


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    """Admin configuration for Loan model."""
    list_display = (
        'loan_number', 'borrower', 'amount_approved', 
        'status', 'application_date', 'disbursement_date', 'outstanding_balance'
    )
    list_filter = (
        'status', 'repayment_frequency', 
        'application_date', 'disbursement_date'
    )
    search_fields = (
        'loan_number', 'borrower__first_name', 'borrower__last_name', 
        'borrower__borrower_id'
    )
    readonly_fields = (
        'loan_number', 'total_interest', 'total_amount', 
        'outstanding_balance', 'created_at', 'updated_at'
    )
    ordering = ('-application_date',)
    
    fieldsets = (
        ('Loan Information', {
            'fields': (
                'loan_number', 'borrower', 'status'
            )
        }),
        ('Loan Details', {
            'fields': (
                'amount_requested', 'amount_approved', 'interest_rate', 
                'duration_months', 'repayment_frequency', 'processing_fee'
            )
        }),
        ('Dates', {
            'fields': (
                'application_date', 'approval_date', 'disbursement_date', 
                'maturity_date'
            )
        }),
        ('Approval & Disbursement', {
            'fields': ('approved_by', 'disbursed_by')
        }),
        ('Calculated Fields', {
            'fields': ('total_interest', 'total_amount', 'outstanding_balance'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': (
                'application_notes', 'approval_notes', 'rejection_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on loan status."""
        readonly = list(self.readonly_fields)
        
        if obj and obj.status in ['disbursed', 'active', 'completed']:
            readonly.extend([
                'borrower', 'amount_requested', 
                'amount_approved', 'interest_rate', 'duration_months'
            ])
        
        return readonly


@admin.register(RepaymentSchedule)
class RepaymentScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for RepaymentSchedule model."""
    list_display = (
        'loan', 'installment_number', 'due_date', 'amount_due',
        'status', 'days_overdue_display'
    )
    list_filter = ('status', 'due_date', 'is_group')
    search_fields = (
        'loan__loan_number', 'loan__borrower__first_name',
        'loan__borrower__last_name'
    )
    readonly_fields = ('days_overdue_display',)
    ordering = ('loan', 'installment_number')

    fieldsets = (
        ('Schedule Information', {
            'fields': ('loan', 'installment_number', 'due_date', 'amount_due')
        }),
        ('Status', {
            'fields': ('status', 'is_group', 'notes')
        }),
    )
    
    def days_overdue_display(self, obj):
        """Display days overdue with color coding."""
        days = obj.days_overdue
        if days > 0:
            if days <= 7:
                color = 'orange'
            elif days <= 30:
                color = 'red'
            else:
                color = 'darkred'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} days</span>',
                color, days
            )
        return '-'
    days_overdue_display.short_description = 'Days Overdue'


@admin.register(LoanPenalty)
class LoanPenaltyAdmin(admin.ModelAdmin):
    """Admin configuration for LoanPenalty model."""
    list_display = (
        'loan', 'penalty_type', 'amount', 'status',
        'applied_date', 'cleared_date'
    )
    list_filter = ('penalty_type', 'status', 'applied_date')
    search_fields = (
        'loan__loan_number', 'loan__borrower__first_name',
        'loan__borrower__last_name'
    )
    readonly_fields = ('applied_date',)
    ordering = ('-applied_date',)

    fieldsets = (
        ('Penalty Information', {
            'fields': (
                'loan', 'penalty_type', 'amount', 'status'
            )
        }),
        ('Dates', {
            'fields': ('applied_date', 'cleared_date')
        }),
        ('Details', {
            'fields': ('reason', 'notes')
        }),
    )


