"""
Core models and abstract base classes for the microfinance system.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from datetime import datetime, date, timedelta


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating 'created_at' and 'updated_at' fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    """
    Abstract base class that adds audit fields for tracking who created/modified records.
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='%(class)s_created',
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='%(class)s_updated',
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class StatusChoices(models.TextChoices):
    """Common status choices used across the system."""
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    SUSPENDED = 'suspended', 'Suspended'
    DELETED = 'deleted', 'Deleted'


class LoanStatusChoices(models.TextChoices):
    """Loan status choices."""
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    DISBURSED = 'disbursed', 'Disbursed'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    DEFAULTED = 'defaulted', 'Defaulted'
    WRITTEN_OFF = 'written_off', 'Written Off'


class PaymentMethodChoices(models.TextChoices):
    """Payment method choices."""
    CASH = 'cash', 'Cash'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    MOBILE_MONEY = 'mobile_money', 'Mobile Money'
    CHECK = 'check', 'Check'
    OTHER = 'other', 'Other'


class FrequencyChoices(models.TextChoices):
    """Repayment frequency choices."""
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'
    BIWEEKLY = 'biweekly', 'Bi-weekly'
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    ANNUALLY = 'annually', 'Annually'


class GenderChoices(models.TextChoices):
    """Gender choices."""
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    OTHER = 'other', 'Other'


class MaritalStatusChoices(models.TextChoices):
    """Marital status choices."""
    SINGLE = 'single', 'Single'
    MARRIED = 'married', 'Married'
    DIVORCED = 'divorced', 'Divorced'
    WIDOWED = 'widowed', 'Widowed'
    SEPARATED = 'separated', 'Separated'


class IDTypeChoices(models.TextChoices):
    """ID type choices."""
    NATIONAL_ID = 'national_id', 'National ID'
    PASSPORT = 'passport', 'Passport'
    DRIVERS_LICENSE = 'drivers_license', "Driver's License"
    VOTER_ID = 'voter_id', 'Voter ID'
    OTHER = 'other', 'Other'


class AccountTypeChoices(models.TextChoices):
    """Chart of accounts type choices."""
    ASSET = 'asset', 'Asset'
    LIABILITY = 'liability', 'Liability'
    EQUITY = 'equity', 'Equity'
    INCOME = 'income', 'Income'
    EXPENSE = 'expense', 'Expense'


class TransactionTypeChoices(models.TextChoices):
    """Transaction type choices."""
    DEBIT = 'debit', 'Debit'
    CREDIT = 'credit', 'Credit'


class SMSLog(AuditModel):
    """Log SMS messages for audit and tracking."""

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('pending', 'Pending'),
    ]

    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    template_name = models.CharField(max_length=100, blank=True, null=True)
    provider = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_response = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField()
    delivered_at = models.DateTimeField(blank=True, null=True)

    # Optional foreign key to link with specific records
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'sms_logs'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['phone_number', '-sent_at']),
            models.Index(fields=['status', '-sent_at']),
            models.Index(fields=['template_name', '-sent_at']),
        ]

    def __str__(self):
        return f"SMS to {self.phone_number} - {self.status} at {self.sent_at}"


# ============ SYSTEM SETTINGS MODELS ============

class SystemSetting(models.Model):
    """Model for storing system-wide settings."""
    SETTING_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('json', 'JSON'),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='text')
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f"{self.key}: {self.value}"

    def get_value(self):
        """Return the value in the appropriate type."""
        if self.setting_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes', 'on']
        elif self.setting_type == 'number':
            try:
                return float(self.value)
            except ValueError:
                return 0
        elif self.setting_type == 'json':
            import json
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return {}
        else:
            return self.value


class CompanyProfile(models.Model):
    """Model for storing company/organization information."""
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)

    # Contact Information
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, default='')
    country = models.CharField(max_length=100, default='Tanzania')

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # Logo and Branding
    logo = models.ImageField(upload_to='company/', blank=True, null=True)

    # Financial Information
    base_currency = models.CharField(max_length=10, default='TSH')
    financial_year_start = models.DateField()

    # Settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profiles'

    def __str__(self):
        return self.name

    @classmethod
    def get_active_company(cls):
        """Get the active company profile."""
        return cls.objects.filter(is_active=True).first()


class Branch(models.Model):
    """Model for managing company branches."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)

    # Contact Information
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Branch Manager
    manager_name = models.CharField(max_length=200, blank=True, null=True)
    manager_phone = models.CharField(max_length=20, blank=True, null=True)
    manager_email = models.EmailField(blank=True, null=True)

    # Settings
    is_active = models.BooleanField(default=True)
    is_head_office = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'

    def __str__(self):
        return f"{self.name} ({self.code})"


class LoanCategory(models.Model):
    """Model for managing loan categories."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    # Interest Settings
    default_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    min_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    max_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)

    # Loan Amount Settings
    min_loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_loan_amount = models.DecimalField(max_digits=15, decimal_places=2)

    # Term Settings
    min_term_months = models.PositiveIntegerField()
    max_term_months = models.PositiveIntegerField()

    # Fees and Charges
    processing_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    processing_fee_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Settings
    is_active = models.BooleanField(default=True)
    requires_collateral = models.BooleanField(default=False)
    requires_guarantor = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Loan Category'
        verbose_name_plural = 'Loan Categories'

    def __str__(self):
        return f"{self.name} ({self.code})"


class PenaltyConfiguration(models.Model):
    """Model for configuring penalties and charges."""
    PENALTY_TYPES = [
        ('percentage', 'Percentage of Overdue Amount'),
        ('fixed', 'Fixed Amount'),
        ('daily', 'Daily Charge'),
    ]

    name = models.CharField(max_length=200)
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPES)

    # Penalty Rates
    percentage_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Application Rules
    grace_period_days = models.PositiveIntegerField(default=0)
    max_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # Settings
    is_active = models.BooleanField(default=True)
    applies_to_all_loans = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Penalty Configuration'
        verbose_name_plural = 'Penalty Configurations'

    def __str__(self):
        return self.name


class PublicHoliday(models.Model):
    """Model for managing public holidays."""
    name = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    is_recurring = models.BooleanField(default=False, help_text="If true, this holiday occurs every year")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        unique_together = ['name', 'date']
        verbose_name = 'Public Holiday'
        verbose_name_plural = 'Public Holidays'

    def __str__(self):
        return f"{self.name} - {self.date}"


class WorkingMode(models.Model):
    """Model for managing working mode settings."""
    TIMEZONE_CHOICES = [
        ('UTC', 'UTC'),
        ('Africa/Dar_es_Salaam', 'East Africa Time (Tanzania)'),
        ('Asia/Kolkata', 'India Standard Time'),
        ('Europe/London', 'Greenwich Mean Time'),
        ('America/New_York', 'Eastern Time'),
    ]

    name = models.CharField(max_length=200, default="Default Working Mode")
    
    # Working Days
    monday_enabled = models.BooleanField(default=True)
    tuesday_enabled = models.BooleanField(default=True)
    wednesday_enabled = models.BooleanField(default=True)
    thursday_enabled = models.BooleanField(default=True)
    friday_enabled = models.BooleanField(default=True)
    saturday_enabled = models.BooleanField(default=False)
    sunday_enabled = models.BooleanField(default=False)
    
    # Working Hours
    start_time = models.TimeField(default='08:00:00')
    end_time = models.TimeField(default='17:00:00')
    lunch_start = models.TimeField(default='12:00:00')
    lunch_end = models.TimeField(default='13:00:00')
    
    # Settings
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='Africa/Dar_es_Salaam')
    allow_backdating = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', 'name']
        verbose_name = 'Working Mode'
        verbose_name_plural = 'Working Modes'

    def __str__(self):
        return self.name

    @property
    def lunch_duration(self):
        """Lunch break duration in hours."""
        start = datetime.combine(date.today(), self.lunch_start)
        end = datetime.combine(date.today(), self.lunch_end)
        if end < start:
            end += timedelta(days=1)
        return round((end - start).total_seconds() / 3600, 2)

    @property
    def total_working_hours(self):
        """Total configured working-window hours (start to end)."""
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        if end < start:
            end += timedelta(days=1)

        return round((end - start).total_seconds() / 3600, 2)

    @property
    def net_working_hours(self):
        """Net daily working hours after lunch break."""
        net_hours = self.total_working_hours - self.lunch_duration
        return round(max(net_hours, 0), 2)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Keep one active configuration at a time.
        if self.is_active:
            WorkingMode.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)

    @classmethod
    def get_active_mode(cls):
        """Get the active working mode."""
        return cls.objects.filter(is_active=True).order_by('-updated_at', 'name').first()


class LoanSector(models.Model):
    """Model for managing loan sectors/industries."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Risk Settings
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ], default='medium')
    
    # Requirements
    min_loan_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    max_loan_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Loan Sector'
        verbose_name_plural = 'Loan Sectors'

    def __str__(self):
        return f"{self.name} ({self.code})"


class IncomeSource(models.Model):
    """Model for managing income sources."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Categorization
    source_type = models.CharField(max_length=50, choices=[
        ('operational', 'Operational Income'),
        ('investment', 'Investment Income'),
        ('other', 'Other Income'),
    ], default='operational')
    
    # Settings
    is_active = models.BooleanField(default=True)
    requires_documentation = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Income Source'
        verbose_name_plural = 'Income Sources'

    def __str__(self):
        return f"{self.name} ({self.code})"


class ExpenseCategory(models.Model):
    """Model for managing expense categories."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Categorization
    category_type = models.CharField(max_length=50, choices=[
        ('operational', 'Operational Expense'),
        ('administrative', 'Administrative Expense'),
        ('financial', 'Financial Expense'),
        ('other', 'Other Expense'),
    ], default='operational')
    
    # Budget Settings
    monthly_budget_limit = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    requires_approval = models.BooleanField(default=False)
    
    # Settings
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return f"{self.name} ({self.code})"


class AssetCategory(models.Model):
    """Model for managing fixed asset categories."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Depreciation Settings
    depreciation_method = models.CharField(max_length=50, choices=[
        ('straight_line', 'Straight Line'),
        ('declining_balance', 'Declining Balance'),
        ('sum_of_years', 'Sum of Years Digits'),
        ('units_of_production', 'Units of Production'),
    ], default='straight_line')
    
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    useful_life_years = models.PositiveIntegerField(default=5)
    
    # Settings
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Asset Category'
        verbose_name_plural = 'Asset Categories'

    def __str__(self):
        return f"{self.name} ({self.code})"


class BankAccount(models.Model):
    """Model for managing bank accounts and cash."""
    ACCOUNT_TYPES = [
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('cash', 'Cash Account'),
        ('credit', 'Credit Account'),
        ('loan', 'Loan Account'),
    ]

    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    
    # Bank Details
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    bank_branch = models.CharField(max_length=200, blank=True, null=True)
    swift_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Balance Information
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        verbose_name = 'Bank Account'
        verbose_name_plural = 'Bank Accounts'

    def __str__(self):
        return f"{self.name} ({self.account_number})"

    def save(self, *args, **kwargs):
        # Ensure only one default account
        if self.is_default:
            BankAccount.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


