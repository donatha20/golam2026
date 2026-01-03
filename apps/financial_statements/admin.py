"""
Admin configuration for Financial Statements app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AccountingPeriod, FinancialStatementTemplate, ClosingEntry,
    FinancialStatementRun, AccountClassification, BudgetPeriod, BudgetLine
)


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'is_year_end', 'is_current_period', 'closed_by']
    list_filter = ['status', 'is_year_end', 'start_date']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'closed_at']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('name', 'start_date', 'end_date', 'is_year_end')
        }),
        ('Status', {
            'fields': ('status', 'closed_by', 'closed_at', 'notes')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_current_period(self, obj):
        return obj.is_current_period
    is_current_period.boolean = True
    is_current_period.short_description = 'Current'


@admin.register(FinancialStatementTemplate)
class FinancialStatementTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'statement_type', 'is_default', 'is_active', 'created_by', 'created_at']
    list_filter = ['statement_type', 'is_default', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'statement_type', 'is_default', 'is_active')
        }),
        ('Configuration', {
            'fields': ('template_data',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ClosingEntry)
class ClosingEntryAdmin(admin.ModelAdmin):
    list_display = ['period', 'closing_type', 'amount', 'journal_entry', 'created_by', 'created_at']
    list_filter = ['closing_type', 'period']
    search_fields = ['description', 'period__name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Closing Entry Information', {
            'fields': ('period', 'closing_type', 'journal_entry', 'amount')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FinancialStatementRun)
class FinancialStatementRunAdmin(admin.ModelAdmin):
    list_display = ['statement_type', 'period', 'status', 'created_by', 'created_at', 'duration_display']
    list_filter = ['statement_type', 'status', 'created_at']
    search_fields = ['period__name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'duration_display']
    
    fieldsets = (
        ('Statement Information', {
            'fields': ('statement_type', 'period', 'comparison_period', 'status')
        }),
        ('Parameters & Results', {
            'fields': ('parameters', 'results', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Generated Files', {
            'fields': ('pdf_file', 'excel_file')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        duration = obj.duration
        if duration:
            return str(duration)
        return '-'
    duration_display.short_description = 'Duration'


@admin.register(AccountClassification)
class AccountClassificationAdmin(admin.ModelAdmin):
    list_display = ['account', 'classification_type', 'sort_order', 'is_contra_account', 'created_by']
    list_filter = ['classification_type', 'is_contra_account']
    search_fields = ['account__account_name', 'account__account_code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Classification Information', {
            'fields': ('account', 'classification_type', 'sort_order', 'is_contra_account')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 0
    fields = ['account', 'budgeted_amount', 'notes']


@admin.register(BudgetPeriod)
class BudgetPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'start_date']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [BudgetLineInline]
    
    fieldsets = (
        ('Budget Information', {
            'fields': ('name', 'start_date', 'end_date', 'is_active')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ['budget_period', 'account', 'budgeted_amount', 'created_by', 'created_at']
    list_filter = ['budget_period', 'account__account_type']
    search_fields = ['budget_period__name', 'account__account_name', 'account__account_code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Budget Line Information', {
            'fields': ('budget_period', 'account', 'budgeted_amount')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
