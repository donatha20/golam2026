"""
Admin configuration for repayment management.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    LoanRepaymentSchedule, Payment, PaymentAllocation, PaymentHistory,
    OutstandingBalance, DailyCollection, CollectionSummary
)


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    readonly_fields = ['total_allocated', 'allocation_date']


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ['action_date', 'performed_by']


@admin.register(LoanRepaymentSchedule)
class LoanRepaymentScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'loan', 'installment_number', 'due_date', 'total_amount', 'total_paid',
        'outstanding_amount', 'payment_status', 'days_overdue'
    ]
    list_filter = [
        'payment_status', 'is_paid', 'is_adjusted', 'loan__status'
    ]
    search_fields = [
        'loan__loan_number', 'loan__borrower__first_name', 'loan__borrower__last_name'
    ]
    readonly_fields = [
        'outstanding_amount', 'outstanding_principal', 'outstanding_interest',
        'outstanding_penalty', 'outstanding_fees', 'payment_percentage',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'due_date'
    ordering = ['loan', 'installment_number']
    
    fieldsets = (
        ('Installment Information', {
            'fields': ('loan', 'installment_number', 'due_date')
        }),
        ('Scheduled Amounts', {
            'fields': (
                'scheduled_principal', 'scheduled_interest', 'scheduled_total'
            )
        }),
        ('Current Amounts', {
            'fields': (
                'principal_amount', 'interest_amount', 'penalty_amount', 
                'fees_amount', 'total_amount'
            )
        }),
        ('Paid Amounts', {
            'fields': (
                'principal_paid', 'interest_paid', 'penalty_paid', 
                'fees_paid', 'total_paid'
            )
        }),
        ('Outstanding Amounts', {
            'fields': (
                'outstanding_principal', 'outstanding_interest', 'outstanding_penalty',
                'outstanding_fees', 'outstanding_amount', 'payment_percentage'
            ),
            'classes': ('collapse',)
        }),
        ('Balance Information', {
            'fields': ('opening_balance', 'closing_balance')
        }),
        ('Status Information', {
            'fields': (
                'payment_status', 'is_paid', 'paid_date', 'days_overdue',
                'last_payment_date', 'penalty_calculation_date'
            )
        }),
        ('Adjustment Information', {
            'fields': (
                'is_adjusted', 'adjustment_reason', 'adjusted_by', 'adjustment_date'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def outstanding_amount(self, obj):
        return f"₹{obj.outstanding_amount:,.2f}"
    outstanding_amount.short_description = "Outstanding Amount"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_reference', 'loan', 'borrower', 'amount', 'payment_method',
        'payment_date', 'status', 'is_verified', 'is_reversed'
    ]
    list_filter = [
        'status', 'payment_method', 'payment_type', 'is_verified', 'is_reversed',
        'payment_date'
    ]
    search_fields = [
        'payment_reference', 'loan__loan_number', 'borrower__first_name',
        'borrower__last_name', 'receipt_number', 'transaction_id'
    ]
    readonly_fields = [
        'payment_reference', 'total_allocated', 'unallocated_amount',
        'is_fully_allocated', 'loan_balance_before', 'loan_balance_after',
        'processed_date', 'created_at', 'updated_at'
    ]
    inlines = [PaymentAllocationInline, PaymentHistoryInline]
    date_hierarchy = 'payment_date'
    ordering = ['-payment_date', '-created_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_reference', 'loan', 'borrower', 'amount', 'payment_method'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_date', 'payment_type', 'receipt_number', 'transaction_id',
                'external_reference', 'notes'
            )
        }),
        ('Allocation Breakdown', {
            'fields': (
                'principal_paid', 'interest_paid', 'penalty_paid', 'fees_paid',
                'advance_payment', 'total_allocated', 'unallocated_amount'
            )
        }),
        ('Status Information', {
            'fields': (
                'status', 'processed_date', 'collected_by'
            )
        }),
        ('Verification', {
            'fields': (
                'is_verified', 'verified_by', 'verification_date', 'verification_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Reversal Information', {
            'fields': (
                'is_reversed', 'reversed_by', 'reversal_date', 'reversal_reason',
                'original_payment'
            ),
            'classes': ('collapse',)
        }),
        ('Balance Impact', {
            'fields': ('loan_balance_before', 'loan_balance_after'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.status == 'completed':
            # Make most fields readonly for completed payments
            readonly_fields.extend([
                'loan', 'borrower', 'amount', 'payment_method', 'payment_date',
                'payment_type', 'principal_paid', 'interest_paid', 'penalty_paid',
                'fees_paid', 'advance_payment'
            ])
        return readonly_fields


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'installment', 'total_allocated', 'principal_allocated',
        'interest_allocated', 'penalty_allocated', 'fees_allocated'
    ]
    list_filter = ['allocation_date']
    search_fields = [
        'payment__payment_reference', 'installment__loan__loan_number'
    ]
    readonly_fields = ['total_allocated', 'allocation_date']
    ordering = ['-allocation_date']


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'action_type', 'action_date', 'performed_by'
    ]
    list_filter = ['action_type', 'action_date']
    search_fields = [
        'payment__payment_reference', 'notes'
    ]
    readonly_fields = ['action_date']
    ordering = ['-action_date']


@admin.register(OutstandingBalance)
class OutstandingBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'loan', 'balance_date', 'total_outstanding', 'principal_outstanding',
        'interest_outstanding', 'penalty_outstanding', 'is_current', 'days_overdue'
    ]
    list_filter = ['is_current', 'balance_date', 'days_overdue']
    search_fields = ['loan__loan_number', 'loan__borrower__first_name']
    readonly_fields = ['total_outstanding']
    date_hierarchy = 'balance_date'
    ordering = ['-balance_date']


@admin.register(DailyCollection)
class DailyCollectionAdmin(admin.ModelAdmin):
    list_display = [
        'collection_date', 'collector', 'total_amount', 'payment_count',
        'target_amount', 'collection_efficiency', 'validation_status', 'has_discrepancy'
    ]
    list_filter = [
        'validation_status', 'has_discrepancy', 'is_verified', 'collection_date',
        'collector'
    ]
    search_fields = [
        'collector__first_name', 'collector__last_name', 'collection_route',
        'collection_area'
    ]
    readonly_fields = [
        'collection_efficiency', 'average_payment', 'target_achievement_percentage',
        'variance_amount', 'collection_rate_per_hour', 'payments_per_hour'
    ]
    date_hierarchy = 'collection_date'
    ordering = ['-collection_date', 'collector']

    fieldsets = (
        ('Collection Information', {
            'fields': ('collection_date', 'collector')
        }),
        ('Targets', {
            'fields': ('target_amount', 'target_payments')
        }),
        ('Collection Summary', {
            'fields': (
                'total_amount', 'payment_count', 'borrower_count',
                'collection_efficiency', 'average_payment'
            )
        }),
        ('Payment Method Breakdown', {
            'fields': (
                'cash_amount', 'cash_count', 'digital_amount', 'digital_count',
                'bank_amount', 'bank_count'
            ),
            'classes': ('collapse',)
        }),
        ('Collection Type Breakdown', {
            'fields': (
                'regular_amount', 'overdue_amount', 'advance_amount', 'penalty_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': (
                'validation_status', 'is_verified', 'verified_by', 'verification_date',
                'verification_notes'
            )
        }),
        ('Discrepancy Information', {
            'fields': (
                'has_discrepancy', 'discrepancy_amount', 'discrepancy_reason',
                'discrepancy_resolved', 'resolved_by', 'resolution_date', 'resolution_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Collection Details', {
            'fields': (
                'collection_start_time', 'collection_end_time', 'collection_duration_hours',
                'collection_route', 'collection_area', 'travel_distance_km'
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'supervisor_comments'),
            'classes': ('collapse',)
        }),
    )

    actions = ['validate_collections', 'recalculate_totals']

    def validate_collections(self, request, queryset):
        validated_count = 0
        for collection in queryset:
            if collection.validate_collection():
                validated_count += 1

        self.message_user(
            request,
            f'{validated_count} collections validated successfully.'
        )
    validate_collections.short_description = "Validate selected collections"

    def recalculate_totals(self, request, queryset):
        for collection in queryset:
            collection.calculate_totals_from_payments()

        self.message_user(
            request,
            f'{queryset.count()} collections recalculated successfully.'
        )
    recalculate_totals.short_description = "Recalculate totals from payments"


@admin.register(CollectionSummary)
class CollectionSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'summary_date', 'total_amount', 'total_payments', 'active_collectors',
        'achievement_percentage', 'validation_status', 'collections_with_discrepancy'
    ]
    list_filter = ['validation_status', 'is_approved', 'summary_date']
    readonly_fields = [
        'total_amount', 'total_payments', 'total_borrowers', 'active_collectors',
        'achievement_percentage', 'cash_total', 'digital_total', 'bank_total',
        'regular_total', 'overdue_total', 'advance_total', 'penalty_total',
        'collections_with_discrepancy', 'total_discrepancy_amount'
    ]
    date_hierarchy = 'summary_date'
    ordering = ['-summary_date']

    fieldsets = (
        ('Summary Information', {
            'fields': ('summary_date',)
        }),
        ('Totals', {
            'fields': (
                'total_amount', 'total_payments', 'total_borrowers', 'active_collectors'
            )
        }),
        ('Target Achievement', {
            'fields': ('total_target', 'achievement_percentage')
        }),
        ('Payment Method Breakdown', {
            'fields': ('cash_total', 'digital_total', 'bank_total'),
            'classes': ('collapse',)
        }),
        ('Collection Type Breakdown', {
            'fields': ('regular_total', 'overdue_total', 'advance_total', 'penalty_total'),
            'classes': ('collapse',)
        }),
        ('Validation Status', {
            'fields': (
                'validation_status', 'collections_with_discrepancy', 'total_discrepancy_amount'
            )
        }),
        ('Approval', {
            'fields': ('is_approved', 'approved_by', 'approval_date', 'approval_notes'),
            'classes': ('collapse',)
        }),
    )

    actions = ['generate_summaries']

    def generate_summaries(self, request, queryset):
        for summary in queryset:
            summary.generate_summary()

        self.message_user(
            request,
            f'{queryset.count()} summaries regenerated successfully.'
        )
    generate_summaries.short_description = "Regenerate selected summaries"
