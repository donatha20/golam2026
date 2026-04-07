"""
Financial Statements models for comprehensive reporting and period management.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date
from apps.accounting.models import Account, JournalEntry

User = get_user_model()


class AccountingPeriod(models.Model):
    """Accounting periods for financial reporting."""
    
    PERIOD_STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('locked', 'Locked'),
    ]
    
    name = models.CharField(max_length=100)  # e.g., "January 2024", "Q1 2024"
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=PERIOD_STATUS_CHOICES, default='open')
    is_year_end = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_periods')
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['start_date', 'end_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    @property
    def is_current_period(self):
        """Check if this is the current accounting period."""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    def can_post_entries(self):
        """Check if journal entries can be posted to this period."""
        return self.status == 'open'


class FinancialStatementTemplate(models.Model):
    """Templates for financial statement formatting."""
    
    STATEMENT_TYPES = [
        ('trial_balance', 'Trial Balance'),
        ('balance_sheet', 'Balance Sheet'),
        ('income_statement', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('equity_statement', 'Statement of Equity'),
    ]
    
    name = models.CharField(max_length=100)
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    template_data = models.JSONField(default=dict)  # Store template configuration
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['statement_type', 'name']
    
    def __str__(self):
        return f"{self.get_statement_type_display()} - {self.name}"


class ClosingEntry(models.Model):
    """Closing entries for period-end procedures."""
    
    CLOSING_TYPES = [
        ('revenue', 'Revenue Closing'),
        ('expense', 'Expense Closing'),
        ('dividend', 'Dividend Closing'),
        ('income_summary', 'Income Summary Closing'),
    ]
    
    period = models.ForeignKey(AccountingPeriod, on_delete=models.CASCADE, related_name='closing_entries')
    closing_type = models.CharField(max_length=20, choices=CLOSING_TYPES)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField()
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['period', 'closing_type']
    
    def __str__(self):
        return f"{self.get_closing_type_display()} - {self.period.name}"


class FinancialStatementRun(models.Model):
    """Track financial statement generation runs."""
    
    STATEMENT_TYPES = [
        ('trial_balance', 'Trial Balance'),
        ('balance_sheet', 'Balance Sheet'),
        ('income_statement', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('complete_set', 'Complete Financial Statements'),
    ]
    
    RUN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    period = models.ForeignKey(AccountingPeriod, on_delete=models.CASCADE)
    comparison_period = models.ForeignKey(
        AccountingPeriod, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='comparison_runs'
    )
    status = models.CharField(max_length=10, choices=RUN_STATUS_CHOICES, default='pending')
    parameters = models.JSONField(default=dict)  # Store generation parameters
    results = models.JSONField(default=dict)  # Store generated statement data
    error_message = models.TextField(blank=True, null=True)
    
    # File storage
    pdf_file = models.FileField(upload_to='financial_statements/pdf/', null=True, blank=True)
    excel_file = models.FileField(upload_to='financial_statements/excel/', null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_statement_type_display()} - {self.period.name}"
    
    @property
    def duration(self):
        """Calculate generation duration."""
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None


class AccountClassification(models.Model):
    """Extended account classifications for financial statement presentation."""
    
    CLASSIFICATION_TYPES = [
        # Balance Sheet Classifications
        ('current_assets', 'Current Assets'),
        ('non_current_assets', 'Non-Current Assets'),
        ('current_liabilities', 'Current Liabilities'),
        ('non_current_liabilities', 'Non-Current Liabilities'),
        ('equity', 'Equity'),
        
        # Income Statement Classifications
        ('operating_revenue', 'Operating Revenue'),
        ('non_operating_revenue', 'Non-Operating Revenue'),
        ('operating_expenses', 'Operating Expenses'),
        ('non_operating_expenses', 'Non-Operating Expenses'),
        
        # Cash Flow Classifications
        ('operating_activities', 'Operating Activities'),
        ('investing_activities', 'Investing Activities'),
        ('financing_activities', 'Financing Activities'),
    ]
    
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='classification')
    classification_type = models.CharField(max_length=30, choices=CLASSIFICATION_TYPES)
    sort_order = models.IntegerField(default=0)
    is_contra_account = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['classification_type', 'sort_order', 'account__account_code']
    
    def __str__(self):
        return f"{self.account.account_name} - {self.get_classification_type_display()}"


class BudgetPeriod(models.Model):
    """Budget periods for comparison with actual results."""
    
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"Budget: {self.name}"


class BudgetLine(models.Model):
    """Budget line items for accounts."""
    
    budget_period = models.ForeignKey(BudgetPeriod, on_delete=models.CASCADE, related_name='budget_lines')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    budgeted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['account__account_code']
        unique_together = ['budget_period', 'account']
    
    def __str__(self):
        return f"{self.budget_period.name} - {self.account.account_name}"
    
    @property
    def variance(self):
        """Calculate variance between budget and actual."""
        # This would be calculated dynamically based on actual account balances
        # Implementation would depend on the specific period and account type
        pass


