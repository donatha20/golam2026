"""
Core models and abstract base classes for the microfinance system.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone


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
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # Logo and Branding
    logo = models.ImageField(upload_to='company/', blank=True, null=True)

    # Financial Information
    base_currency = models.CharField(max_length=10, default='INR')
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
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

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
