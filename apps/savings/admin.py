"""
Admin configuration for savings management.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SavingsProduct, SavingsLoanRule, SavingsAccount, SavingsTransaction,
    SavingsInterestCalculation, SavingsAccountHold
)


@admin.register(SavingsProduct)
class SavingsProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'interest_rate', 'minimum_balance', 'minimum_opening_balance',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'interest_calculation_method', 'interest_posting_frequency']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Interest Settings', {
            'fields': (
                'interest_rate', 'interest_calculation_method', 'interest_posting_frequency'
            )
        }),
        ('Balance Requirements', {
            'fields': ('minimum_opening_balance', 'minimum_balance', 'maximum_balance')
        }),
        ('Transaction Limits', {
            'fields': (
                'minimum_deposit', 'maximum_deposit_per_day',
                'minimum_withdrawal', 'maximum_withdrawal_per_day'
            )
        }),
        ('Fees', {
            'fields': ('account_maintenance_fee', 'withdrawal_fee')
        }),
        ('Settings', {
            'fields': ('is_active', 'requires_approval', 'allow_overdraft')
        }),
    )


@admin.register(SavingsLoanRule)
class SavingsLoanRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'loan_category', 'rule_type', 'is_active', 'is_mandatory', 'created_at'
    ]
    list_filter = ['rule_type', 'is_active', 'is_mandatory', 'loan_category']
    search_fields = ['name', 'loan_category', 'description']
    ordering = ['loan_category', 'rule_type']


class SavingsTransactionInline(admin.TabularInline):
    model = SavingsTransaction
    extra = 0
    readonly_fields = ['transaction_id', 'balance_after', 'created_at', 'processed_by']
    fields = [
        'transaction_type', 'amount', 'description', 'transaction_date',
        'status', 'balance_after', 'processed_by'
    ]


class SavingsInterestCalculationInline(admin.TabularInline):
    model = SavingsInterestCalculation
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class SavingsAccountHoldInline(admin.TabularInline):
    model = SavingsAccountHold
    extra = 0
    readonly_fields = ['created_at', 'created_by']


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = [
        'account_number', 'borrower', 'savings_product', 'balance',
        'status', 'opened_date', 'is_dormant'
    ]
    list_filter = ['status', 'is_dormant', 'savings_product', 'opened_date']
    search_fields = [
        'account_number', 'borrower__first_name', 'borrower__last_name',
        'borrower__phone_number'
    ]
    readonly_fields = [
        'account_number', 'available_balance', 'total_holds',
        'days_since_last_transaction', 'is_eligible_for_loan'
    ]
    inlines = [SavingsTransactionInline, SavingsInterestCalculationInline, SavingsAccountHoldInline]
    
    fieldsets = (
        ('Account Information', {
            'fields': ('account_number', 'borrower', 'savings_product')
        }),
        ('Balance Information', {
            'fields': ('balance', 'available_balance', 'total_holds')
        }),
        ('Interest Information', {
            'fields': (
                'accrued_interest', 'last_interest_calculation', 'last_interest_posting',
                'total_interest_earned'
            )
        }),
        ('Account Status', {
            'fields': (
                'status', 'opened_date', 'opened_by', 'closed_date', 'closed_by',
                'closure_reason'
            )
        }),
        ('Additional Information', {
            'fields': (
                'is_dormant', 'dormant_date', 'last_transaction_date',
                'linked_loan_id', 'notes'
            )
        }),
        ('Calculated Fields', {
            'fields': ('days_since_last_transaction', 'is_eligible_for_loan'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'savings_account', 'transaction_type', 'amount',
        'balance_after', 'status', 'transaction_date', 'processed_by'
    ]
    list_filter = ['transaction_type', 'status', 'transaction_date']
    search_fields = [
        'transaction_id', 'savings_account__account_number',
        'savings_account__borrower__first_name', 'savings_account__borrower__last_name'
    ]
    readonly_fields = ['transaction_id', 'balance_after', 'created_at', 'processed_by']
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_id', 'savings_account', 'transaction_type', 'amount')
        }),
        ('Details', {
            'fields': ('description', 'transaction_date', 'reference_number')
        }),
        ('Status', {
            'fields': ('status', 'balance_after', 'processed_by')
        }),
    )


@admin.register(SavingsInterestCalculation)
class SavingsInterestCalculationAdmin(admin.ModelAdmin):
    list_display = [
        'savings_account', 'calculation_date', 'period_start_date', 'period_end_date',
        'interest_amount', 'is_posted', 'posted_date'
    ]
    list_filter = ['is_posted', 'calculation_date', 'posted_date']
    search_fields = ['savings_account__account_number', 'savings_account__borrower__first_name']
    readonly_fields = ['created_at', 'created_by']
    date_hierarchy = 'calculation_date'


@admin.register(SavingsAccountHold)
class SavingsAccountHoldAdmin(admin.ModelAdmin):
    list_display = [
        'savings_account', 'hold_type', 'hold_amount', 'status',
        'hold_date', 'expiry_date', 'released_date'
    ]
    list_filter = ['hold_type', 'status', 'hold_date']
    search_fields = ['savings_account__account_number', 'reference_number', 'reason']
    readonly_fields = ['created_at', 'created_by']
    date_hierarchy = 'hold_date'


