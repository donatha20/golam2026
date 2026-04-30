from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models, transaction
from django.db.models import F
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from functools import cached_property
from apps.core.models import AuditModel, LoanStatusChoices, FrequencyChoices
from apps.accounts.models import CustomUser
from apps.borrowers.models import Borrower
import random
import string


class InterestTypeChoices(models.TextChoices):
    FLAT = 'flat', 'Flat'
    REDUCING = 'reducing', 'Reducing Balance'
    OTHER = 'other', 'Other'


class RepaymentStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    DUE = 'due', 'Due'
    PAID = 'paid', 'Paid'
    PARTIAL = 'partial', 'Partially Paid'
    MISSED = 'missed', 'Missed'
    ROLLED_OVER = 'rolled_over', 'Rolled Over'
    DEFAULTED = 'defaulted', 'Defaulted'


# Constants for loan calculations and thresholds
class LoanConstants:
    """Constants used in loan calculations and status determination."""
    # Frequency to installment multiplier (days per period)
    DAYS_PER_MONTH = 30  # Used for daily frequency: duration_months * 30
    WEEKS_PER_MONTH = 4.29  # Average weeks per month
    INSTALLMENTS_PER_QUARTER = 1  # One payment per quarter
    
    # NPL thresholds (days overdue)
    NPL_WATCH_DAYS = 90        # Watch category threshold
    NPL_SUBSTANDARD_DAYS = 180 # Substandard category threshold
    NPL_DOUBTFUL_DAYS = 270    # Doubtful category threshold
    NPL_LOSS_DAYS = 365        # Loss category threshold
    
    # Repayment schedule thresholds
    DEFAULTED_DAYS = 30  # Days overdue before marking as defaulted
    
    # Penalty calculations
    MISSED_PAYMENT_PENALTY_DEFAULT = Decimal('500.00')


class RepaymentStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    DUE = 'due', 'Due'
    PAID = 'paid', 'Paid'
    PARTIAL = 'partial', 'Partially Paid'
    MISSED = 'missed', 'Missed'
    ROLLED_OVER = 'rolled_over', 'Rolled Over'
    DEFAULTED = 'defaulted', 'Defaulted'


class PenaltyStatusChoices(models.TextChoices):
    APPLIED = 'applied', 'Applied'
    CLEARED = 'cleared', 'Cleared'


class PaymentMethodChoices(models.TextChoices):
    CASH = 'cash', 'Cash'
    MOBILE_MONEY = 'mobile_money', 'Mobile Money'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'


class RepaymentTypeChoices(models.TextChoices):
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'


class NPLCategoryChoices(models.TextChoices):
    """Non-Performing Loan classification categories based on days overdue."""
    PERFORMING = 'performing', 'Performing'
    WATCH = 'watch', 'Watch (90-180 days)'
    SUBSTANDARD = 'substandard', 'Substandard (180-270 days)'
    DOUBTFUL = 'doubtful', 'Doubtful (270-365 days)'
    LOSS = 'loss', 'Loss (365+ days)'


class NPLStatusChoices(models.TextChoices):
    """Status of NPL resolution efforts."""
    NONE = 'none', 'Not Classified'
    UNDER_REVIEW = 'under_review', 'Under Review'
    RECOVERY_ACTIVE = 'recovery_active', 'Active Recovery'
    RESTRUCTURED = 'restructured', 'Restructured'
    LEGAL_ACTION = 'legal_action', 'Legal Action'
    WRITE_OFF_PENDING = 'write_off_pending', 'Write-off Pending'
    WRITTEN_OFF = 'written_off', 'Written Off'


class LoanQuerySet(models.QuerySet):
    def overdue(self):
        """Get loans with overdue repayment schedules."""
        today = timezone.now().date()
        return self.filter(
            repayment_schedules__due_date__lt=today,
            repayment_schedules__status__in=[
                RepaymentStatusChoices.PENDING,
                RepaymentStatusChoices.DUE,
                RepaymentStatusChoices.PARTIAL,
                RepaymentStatusChoices.MISSED
            ],
            status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
        ).distinct()

    def portfolio_at_risk(self):
        """Get loans with missed or defaulted payments."""
        return self.filter(
            repayment_schedules__status__in=[
                RepaymentStatusChoices.MISSED,
                RepaymentStatusChoices.DEFAULTED
            ]
        ).distinct()

    def fully_paid(self):
        """Get loans with zero outstanding balance."""
        return self.filter(outstanding_balance=0, status=LoanStatusChoices.CLOSED)

    def non_performing(self):
        """Get all non-performing loans (90+ days overdue)."""
        return self.filter(is_npl=True)

    def npl_by_category(self, category):
        """Filter NPLs by category."""
        return self.filter(is_npl=True, npl_category=category)

    def watch_loans(self):
        """Get loans in Watch category (90-180 days overdue)."""
        return self.filter(npl_category=NPLCategoryChoices.WATCH)

    def substandard_loans(self):
        """Get loans in Substandard category (180-270 days overdue)."""
        return self.filter(npl_category=NPLCategoryChoices.SUBSTANDARD)

    def doubtful_loans(self):
        """Get loans in Doubtful category (270-365 days overdue)."""
        return self.filter(npl_category=NPLCategoryChoices.DOUBTFUL)

    def loss_loans(self):
        """Get loans in Loss category (365+ days overdue)."""
        return self.filter(npl_category=NPLCategoryChoices.LOSS)


class LoanManager(models.Manager):
    def get_queryset(self):
        return LoanQuerySet(self.model, using=self._db)

    def overdue(self):
        return self.get_queryset().overdue()

    def portfolio_at_risk(self):
        return self.get_queryset().portfolio_at_risk()

    def fully_paid(self):
        return self.get_queryset().fully_paid()

    def non_performing(self):
        return self.get_queryset().non_performing()

    def watch_loans(self):
        return self.get_queryset().watch_loans()

    def substandard_loans(self):
        return self.get_queryset().substandard_loans()

    def doubtful_loans(self):
        return self.get_queryset().doubtful_loans()

    def loss_loans(self):
        return self.get_queryset().loss_loans()


class Loan(AuditModel):
    loan_number = models.CharField(max_length=20, unique=True, editable=False)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='loans')
    
    # Basic loan information
    loan_category = models.CharField(max_length=50, blank=True, null=True)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    amount_approved = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],  # Must be positive if set
        help_text="Approved loan amount must be greater than zero"
    )
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    proposed_project = models.CharField(max_length=255, blank=True, null=True)
    
    # Collateral information
    collateral_name = models.CharField(max_length=255, blank=True, null=True)
    collateral_worth = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],  # Cannot be negative
        help_text="Collateral value must be non-negative"
    )
    collateral_withheld = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],  # Cannot be negative
        help_text="Withheld collateral amount must be non-negative"
    )
    
    # Payment and disbursement
    repayment_frequency = models.CharField(
        max_length=20, 
        choices=FrequencyChoices.choices, 
        default=FrequencyChoices.MONTHLY
    )
    repayment_type = models.CharField(
        max_length=20, 
        choices=RepaymentTypeChoices.choices, 
        default=RepaymentTypeChoices.MONTHLY
    )
    processing_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],  # Cannot be negative
        help_text="Processing fee must be non-negative"
    )
    loan_fees_applied = models.BooleanField(default=False)
    
    # Disbursement information
    pay_method = models.CharField(
        max_length=20, 
        choices=PaymentMethodChoices.choices, 
        default=PaymentMethodChoices.CASH
    )
    payment_account = models.CharField(max_length=100, blank=True, null=True)
    loan_officer = models.CharField(max_length=100, blank=True, null=True)
    start_payment_date = models.DateField(null=True, blank=True)

    # Dates
    application_date = models.DateField(default=timezone.now)
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(
        null=True, blank=True,
        help_text="Date when loan was fully paid/completed"
    )

    # Status and approval
    status = models.CharField(
        max_length=15, 
        choices=LoanStatusChoices.choices, 
        default=LoanStatusChoices.PENDING
    )
    approved_by = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, null=True, blank=True, 
        related_name='approved_loans'
    )
    rejected_by = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, null=True, blank=True, 
        related_name='rejected_loans'
    )
    rejection_date = models.DateField(null=True, blank=True)
    
    # Rejection reversal tracking
    is_rejection_reversed = models.BooleanField(
        default=False,
        help_text="Whether rejection has been reversed"
    )
    reversed_rejection_date = models.DateField(
        null=True, blank=True,
        help_text="Date when rejection was reversed"
    )
    rejection_reversed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reversed_loan_rejections',
        help_text="User who reversed the rejection"
    )
    reversal_reason = models.TextField(
        blank=True, null=True,
        help_text="Reason for reversing the rejection"
    )
    
    disbursed_by = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, null=True, blank=True, 
        related_name='disbursed_loans'
    )

    # Notes and documentation
    application_notes = models.TextField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    supporting_document = models.FileField(upload_to='loan_documents/', blank=True, null=True)

    # Financial calculations
    total_interest = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],  # Cannot be negative
        help_text="Total interest amount must be non-negative"
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],  # Must be >= 0
        help_text="Total loan amount must be non-negative"
    )
    outstanding_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],  # Cannot be negative
        help_text="Outstanding balance must be non-negative"
    )
    total_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],  # Cannot be negative
        help_text="Total paid amount must be non-negative"
    )

    # NPL (Non-Performing Loan) tracking fields
    is_npl = models.BooleanField(default=False, help_text="Whether this loan is classified as non-performing")
    npl_category = models.CharField(
        max_length=20, 
        choices=NPLCategoryChoices.choices, 
        default=NPLCategoryChoices.PERFORMING,
        help_text="NPL classification based on days overdue"
    )
    npl_status = models.CharField(
        max_length=20, 
        choices=NPLStatusChoices.choices, 
        default=NPLStatusChoices.NONE,
        help_text="Current status of NPL resolution"
    )
    npl_classification_date = models.DateField(
        null=True, blank=True, 
        help_text="Date when loan was classified as NPL"
    )
    npl_provision_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Provision amount set aside for potential loss"
    )
    npl_recovery_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Amount recovered from NPL"
    )
    npl_notes = models.TextField(
        blank=True, null=True, 
        help_text="Notes regarding NPL status and recovery efforts"
    )
    assigned_recovery_officer = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_npl_loans',
        help_text="Officer assigned to handle NPL recovery"
    )
    last_recovery_contact_date = models.DateField(
        null=True, blank=True, 
        help_text="Date of last contact for recovery"
    )
    next_recovery_action_date = models.DateField(
        null=True, blank=True, 
        help_text="Scheduled date for next recovery action"
    )

    objects = LoanManager()

    class Meta:
        ordering = ['-application_date', '-created_at']
        indexes = [
            models.Index(fields=['loan_number']),
            models.Index(fields=['status']),
            models.Index(fields=['borrower']),
            models.Index(fields=['application_date']),
            models.Index(fields=['disbursement_date']),
            models.Index(fields=['is_npl', 'npl_category']),
        ]
        permissions = [
            ('can_reject_loan', 'Can reject pending loans'),
            ('can_reverse_rejection', 'Can reverse rejected loans'),
        ]

    def __str__(self):
        return f"{self.loan_number} - {self.borrower.get_full_name()}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Save loan with atomic transaction to ensure consistency across all calculations."""
        if not self.loan_number:
            self.loan_number = self.generate_loan_number()

        # Normalize legacy typo before any downstream calculations.
        if self.repayment_frequency == FrequencyChoices.EVEY_THREE_DAYS:
            self.repayment_frequency = FrequencyChoices.EVERY_THREE_DAYS
        
        if self.status == LoanStatusChoices.APPROVED and not self.amount_approved:
            self.amount_approved = self.amount_requested

        # Check if we're only updating repayment-related fields (don't recalculate in that case)
        update_fields = kwargs.get('update_fields')
        is_repayment_only_update = (
            update_fields and 
            set(update_fields).issubset({'total_paid', 'outstanding_balance', 'status'})
        )

        existing_snapshot = None
        if self.pk:
            existing_snapshot = Loan.objects.filter(pk=self.pk).values(
                'amount_approved',
                'interest_rate',
                'duration_months',
                'total_interest',
                'total_amount',
            ).first()
        
        if not is_repayment_only_update:
            # Only recalculate loan totals if this is NOT a repayment update
            manual_interest_amount = getattr(self, '_manual_interest_amount', None)
            if manual_interest_amount is not None and self.amount_approved:
                principal = Decimal(str(self.amount_approved)).quantize(Decimal('0.01'))
                manual_interest = Decimal(str(manual_interest_amount)).quantize(Decimal('0.01'))
                self.total_interest = manual_interest
                self.total_amount = principal + manual_interest
                total_paid = Decimal(str(self.total_paid or 0))
                self.outstanding_balance = self.total_amount - total_paid
            
            elif self.amount_approved and self.interest_rate and self.duration_months:
                should_recalculate_totals = True

                # Preserve exact stored totals on status/date-only updates to avoid
                # drift from rounded interest_rate recomputation.
                if existing_snapshot:
                    previous_amount_raw = existing_snapshot.get('amount_approved')
                    previous_amount = Decimal(str(previous_amount_raw or 0))
                    previous_rate = Decimal(str(existing_snapshot.get('interest_rate') or 0))
                    previous_duration = int(existing_snapshot.get('duration_months') or 0)

                    current_amount = Decimal(str(self.amount_approved or 0))
                    current_rate = Decimal(str(self.interest_rate or 0))
                    current_duration = int(self.duration_months or 0)

                    pricing_inputs_unchanged = (
                        previous_amount == current_amount
                        and previous_rate == current_rate
                        and previous_duration == current_duration
                    )

                    previous_total_interest = existing_snapshot.get('total_interest')
                    previous_total_amount = existing_snapshot.get('total_amount')

                    if pricing_inputs_unchanged and previous_total_interest is not None and previous_total_amount is not None:
                        self.total_interest = Decimal(str(previous_total_interest))
                        self.total_amount = Decimal(str(previous_total_amount))
                        total_paid = Decimal(str(self.total_paid or 0))
                        self.outstanding_balance = self.total_amount - total_paid
                        should_recalculate_totals = False
                    else:
                        # Preserve manually entered totals when approval sets
                        # amount_approved from empty to the requested amount.
                        requested_amount = Decimal(str(self.amount_requested or 0))
                        manual_totals_exist = (
                            previous_total_interest is not None
                            and previous_total_amount is not None
                        )
                        approval_defaulted_amount = (
                            previous_amount_raw in (None, '')
                            and current_amount == requested_amount
                        )
                        if manual_totals_exist and approval_defaulted_amount:
                            preserved_interest = Decimal(str(previous_total_interest)).quantize(Decimal('0.01'))
                            self.total_interest = preserved_interest
                            self.total_amount = (current_amount + preserved_interest).quantize(Decimal('0.01'))
                            total_paid = Decimal(str(self.total_paid or 0))
                            self.outstanding_balance = self.total_amount - total_paid
                            should_recalculate_totals = False

                if should_recalculate_totals:
                    self.calculate_loan_totals()
        
        if self.status == LoanStatusChoices.DISBURSED and self.disbursement_date and not self.maturity_date:
            self.calculate_maturity_date()
        
        super().save(*args, **kwargs)

    def generate_loan_number(self):
        """Generate unique loan number using sequential format: LN-0001."""
        last_loan = Loan.objects.filter(
            loan_number__startswith='LN-'
        ).order_by('loan_number').last()
        
        if last_loan:
            last_number = int(last_loan.loan_number[3:])  # Extract digits after 'LN-'
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"LN-{new_number:04d}"

    def calculate_loan_totals(self):
        """Calculate total interest and total amount based on interest type with division guards."""
        if not all([self.amount_approved, self.interest_rate, self.duration_months]):
            return
        
        principal = Decimal(str(self.amount_approved))
        rate = Decimal(str(self.interest_rate)) / 100
        months = Decimal(str(self.duration_months))

        # Interest defaults to flat calculation after legacy product-field removal.
        interest_type = InterestTypeChoices.FLAT

        if interest_type == InterestTypeChoices.REDUCING:
            # Reducing balance (EMI calculation)
            monthly_rate = rate / 12
            n = months
            if monthly_rate > 0 and n > 0:  # Guard against division by zero
                emi = principal * (monthly_rate * (1 + monthly_rate)**n) / ((1 + monthly_rate)**n - 1)
                self.total_amount = emi * n
                self.total_interest = self.total_amount - principal
            else:
                # Zero interest rate or zero duration
                self.total_amount = principal
                self.total_interest = Decimal('0')
        else:
            # Flat rate - guard against zero months
            if months > 0:
                self.total_interest = principal * rate * (months / 12)
            else:
                self.total_interest = Decimal('0')
            self.total_amount = principal + self.total_interest

        self.outstanding_balance = self.total_amount

    def clean(self):
        """Validate loan data before saving."""
        from django.core.exceptions import ValidationError
        errors = {}
        today = timezone.now().date()
        
        # Validate application_date is not in the future
        if self.application_date:
            app_date = self.application_date.date() if hasattr(self.application_date, 'date') else self.application_date
            if app_date > today:
                errors['application_date'] = "Application date cannot be in the future."
        
        # Validate approval_date is after application_date
        if self.approval_date and self.application_date:
            app_date = self.application_date.date() if hasattr(self.application_date, 'date') else self.application_date
            if self.approval_date < app_date:
                errors['approval_date'] = "Approval date cannot be before application date."
        
        # Validate disbursement_date is after or on approval_date
        if self.disbursement_date and self.approval_date:
            if self.disbursement_date < self.approval_date:
                errors['disbursement_date'] = "Disbursement date cannot be before approval date."
        
        # Validate start_payment_date is after or on disbursement_date
        if self.start_payment_date and self.disbursement_date:
            if self.start_payment_date < self.disbursement_date:
                errors['start_payment_date'] = "Start payment date cannot be before disbursement date."
        
        # Validate maturity_date is after disbursement_date
        if self.maturity_date and self.disbursement_date:
            if self.maturity_date <= self.disbursement_date:
                errors['maturity_date'] = "Maturity date must be after disbursement date."
        
        # Validate duration_months is positive
        if self.duration_months and self.duration_months <= 0:
            errors['duration_months'] = "Duration must be a positive number of months."
        
        # Validate interest_rate is not negative
        if self.interest_rate is not None and self.interest_rate < 0:
            errors['interest_rate'] = "Interest rate cannot be negative."
        
        if errors:
            raise ValidationError(errors)
    
    def calculate_maturity_date(self):
        """Calculate loan maturity date."""
        if self.disbursement_date and self.duration_months:
            self.maturity_date = self.disbursement_date + relativedelta(months=self.duration_months)

    @cached_property
    def oldest_overdue_due_date(self):
        """Returns the due_date of the oldest unpaid overdue installment.
        
        Uses @cached_property to prevent N+1 queries when accessed multiple times
        in the same request. Cache valid for instance lifecycle only.
        """
        today = timezone.localdate()

        overdue_statuses = [
            RepaymentStatusChoices.PENDING,
            RepaymentStatusChoices.DUE,
            RepaymentStatusChoices.MISSED,
            RepaymentStatusChoices.DEFAULTED,
            RepaymentStatusChoices.PARTIAL
        ]

        return (
            self.repayment_schedules
            .filter(due_date__lt=today, status__in=overdue_statuses)
            .order_by("due_date")
            .values_list("due_date", flat=True)
            .first()
        )

    @property
    def days_overdue(self):
        """Calculate days overdue based on oldest overdue installment."""
        today = timezone.localdate()
        due = self.oldest_overdue_due_date
        return (today - due).days if due else 0

    @property
    def is_overdue(self):
        """Check if loan has any overdue payments."""
        return (
            self.status in [LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
            and self.oldest_overdue_due_date is not None
        )

    @property
    def is_in_arrears(self):
        """Check if loan is in arrears (1-5 days overdue)."""
        return 1 <= self.days_overdue <= 5

    @property
    def is_in_par(self):
        """Check if loan is in Portfolio at Risk (6-30 days overdue)."""
        return 6 <= self.days_overdue <= 30

    @property
    def is_loss(self):
        """Check if loan is in Loss category (365+ days overdue)."""
        return self.days_overdue > 365

    @property
    def calculated_npl_category(self):
        """Calculate NPL category based on days overdue using defined constants."""
        days = self.days_overdue
        if days >= LoanConstants.NPL_LOSS_DAYS:
            return NPLCategoryChoices.LOSS
        elif days >= LoanConstants.NPL_DOUBTFUL_DAYS:
            return NPLCategoryChoices.DOUBTFUL
        elif days >= LoanConstants.NPL_SUBSTANDARD_DAYS:
            return NPLCategoryChoices.SUBSTANDARD
        elif days >= LoanConstants.NPL_WATCH_DAYS:
            return NPLCategoryChoices.WATCH
        return NPLCategoryChoices.PERFORMING

    @property
    def is_non_performing(self):
        """Check if loan qualifies as non-performing (90+ days overdue)."""
        return self.days_overdue >= 90

    @property
    def provision_rate(self):
        """Get the provision rate based on NPL category."""
        provision_rates = {
            NPLCategoryChoices.PERFORMING: Decimal('0.01'),    # 1%
            NPLCategoryChoices.WATCH: Decimal('0.05'),         # 5%
            NPLCategoryChoices.SUBSTANDARD: Decimal('0.25'),   # 25%
            NPLCategoryChoices.DOUBTFUL: Decimal('0.50'),      # 50%
            NPLCategoryChoices.LOSS: Decimal('1.00'),          # 100%
        }
        return provision_rates.get(self.calculated_npl_category, Decimal('0'))

    @property
    def calculated_provision_amount(self):
        """Calculate provision amount based on outstanding balance and category."""
        return self.outstanding_balance * self.provision_rate

    def update_npl_classification(self, save_loan=True):
        """Update NPL classification based on current days overdue."""
        old_category = self.npl_category
        new_category = self.calculated_npl_category
        
        self.npl_category = new_category
        self.is_npl = self.is_non_performing
        self.npl_provision_amount = self.calculated_provision_amount
        
        # Set classification date if newly classified as NPL
        if not self.npl_classification_date and self.is_npl:
            self.npl_classification_date = timezone.now().date()
        
        # Clear classification date if no longer NPL
        if not self.is_npl and self.npl_classification_date:
            self.npl_classification_date = None
            self.npl_status = NPLStatusChoices.NONE
        
        if save_loan:
            self.save(update_fields=[
                'npl_category', 'is_npl', 'npl_provision_amount', 
                'npl_classification_date', 'npl_status'
            ])
        
        return old_category != new_category

    def update_outstanding_balance(self):
        """Recalculate outstanding balance and update NPL classification accordingly."""
        total_paid = sum(
            repayment.amount_paid 
            for schedule in self.repayment_schedules.all() 
            for repayment in schedule.repayments.all()
        )
        self.total_paid = Decimal(str(total_paid))
        self.outstanding_balance = self.total_amount - self.total_paid
        
        # Update status to closed if fully paid
        if self.outstanding_balance <= 0 and self.status in [
            LoanStatusChoices.ACTIVE, 
            LoanStatusChoices.DISBURSED
        ]:
            self.status = LoanStatusChoices.CLOSED
        
        self.save(update_fields=['outstanding_balance', 'total_paid', 'status'])
        
        # Update NPL classification based on new outstanding balance
        # This ensures ratings change when payments reduce days overdue
        self.update_npl_classification(save_loan=False)  # save already called above

    def disburse(self, disbursed_by):
        """Disburse the loan and generate repayment schedule."""
        if self.status != LoanStatusChoices.APPROVED:
            raise ValueError("Loan must be approved before disbursement")
        
        self.status = LoanStatusChoices.DISBURSED
        self.disbursed_by = disbursed_by
        self.disbursement_date = timezone.now().date()
        self.calculate_maturity_date()
        self.save()
        
        # Generate repayment schedule
        self.generate_repayment_schedule()

    def generate_repayment_schedule(self):
        """Generate repayment schedule based on loan parameters with guards against division by zero."""
        if not self.disbursement_date:
            raise ValueError("Disbursement date is required to generate schedule")

        # Support legacy typo value while keeping the scheduling logic canonical.
        normalized_frequency = self.repayment_frequency
        if normalized_frequency == FrequencyChoices.EVEY_THREE_DAYS:
            normalized_frequency = FrequencyChoices.EVERY_THREE_DAYS
        
        # Clear existing schedules
        self.repayment_schedules.all().delete()
        
        # Determine number of installments based on repayment frequency
        frequency_map = {
            FrequencyChoices.DAILY: int(self.duration_months * LoanConstants.DAYS_PER_MONTH),
            FrequencyChoices.EVERY_THREE_DAYS: max(1, int((self.duration_months * LoanConstants.DAYS_PER_MONTH) / 3)),
            FrequencyChoices.WEEKLY: int(self.duration_months * LoanConstants.WEEKS_PER_MONTH),
            FrequencyChoices.BIWEEKLY: max(1, int((self.duration_months * LoanConstants.WEEKS_PER_MONTH) / 2)),
            FrequencyChoices.MONTHLY: self.duration_months,
            FrequencyChoices.QUARTERLY: max(1, self.duration_months // 3),
            FrequencyChoices.ANNUALLY: max(1, self.duration_months // 12),
        }
        
        num_installments = frequency_map.get(normalized_frequency, self.duration_months)
        # Guard against zero installments to prevent division by zero error
        if num_installments <= 0:
            raise ValueError(f"Invalid number of installments: {num_installments}. Duration months: {self.duration_months}")
        installment_amount = self.total_amount / num_installments
        
        # Calculate interval
        interval_map = {
            FrequencyChoices.DAILY: timedelta(days=1),
            FrequencyChoices.EVERY_THREE_DAYS: timedelta(days=3),
            FrequencyChoices.WEEKLY: timedelta(weeks=1),
            FrequencyChoices.BIWEEKLY: timedelta(weeks=2),
            FrequencyChoices.MONTHLY: relativedelta(months=1),
            FrequencyChoices.QUARTERLY: relativedelta(months=3),
            FrequencyChoices.ANNUALLY: relativedelta(years=1),
        }
        
        start_date = self.start_payment_date or self.disbursement_date
        interval = interval_map.get(normalized_frequency, relativedelta(months=1))
        current_date = start_date
        
        # Create installments
        for i in range(1, num_installments + 1):
            current_date = start_date + (interval * i)
            
            RepaymentSchedule.objects.create(
                loan=self,
                installment_number=i,
                due_date=current_date,
                amount_due=installment_amount,
                status=RepaymentStatusChoices.PENDING
            )


class GroupLoan(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='group_loan')
    group = models.ForeignKey('borrowers.BorrowerGroup', on_delete=models.PROTECT, related_name='group_loans')
    
    class Meta:
        verbose_name = "Group Loan"
        verbose_name_plural = "Group Loans"

    def __str__(self):
        return f"Group Loan: {self.loan.loan_number} for {self.group.name}"


class GroupLoanMember(models.Model):
    group_loan = models.ForeignKey(GroupLoan, on_delete=models.CASCADE, related_name='members')
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    responsibility_share = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        unique_together = ['group_loan', 'borrower']
        verbose_name = "Group Loan Member"
        verbose_name_plural = "Group Loan Members"

    def __str__(self):
        return f"{self.borrower.get_full_name()} - {self.responsibility_share}%"


class LoanDisbursement(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='disbursements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    disbursed_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    disbursement_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    is_redisbursed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-disbursement_date']
        verbose_name = "Loan Disbursement"
        verbose_name_plural = "Loan Disbursements"

    def __str__(self):
        return f"Disbursement for {self.loan.loan_number} - {self.amount}"


class RepaymentSchedule(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayment_schedules')
    due_date = models.DateField()
    amount_due = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Amount due for this installment"
    )
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Amount paid towards this installment"
    )
    status = models.CharField(
        max_length=15, 
        choices=RepaymentStatusChoices.choices, 
        default=RepaymentStatusChoices.PENDING
    )
    installment_number = models.PositiveIntegerField()
    is_group = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['loan', 'installment_number']
        unique_together = ['loan', 'installment_number']
        indexes = [
            models.Index(fields=['loan', 'due_date']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['due_date']),  # Index for queries filtering only by due_date
            models.Index(fields=['status']),     # Index for queries filtering only by status
        ]

    def __str__(self):
        return f"Schedule {self.installment_number} for {self.loan.loan_number}"

    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.status in [RepaymentStatusChoices.MISSED, RepaymentStatusChoices.DEFAULTED]:
            return (timezone.now().date() - self.due_date).days
        return 0

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid."""
        return self.amount_due - self.amount_paid

    def update_status(self):
        """Update schedule status based on payments and due dates."""
        today = timezone.now().date()
        
        if self.amount_paid >= self.amount_due:
            self.status = RepaymentStatusChoices.PAID
        elif self.amount_paid > 0:
            self.status = RepaymentStatusChoices.PARTIAL
        elif self.due_date < today:
            # Overdue logic - use constant threshold
            days_overdue = (today - self.due_date).days
            if days_overdue > LoanConstants.DEFAULTED_DAYS:
                self.status = RepaymentStatusChoices.DEFAULTED
            else:
                self.status = RepaymentStatusChoices.MISSED
        elif self.due_date == today:
            self.status = RepaymentStatusChoices.DUE
        else:
            self.status = RepaymentStatusChoices.PENDING
        
        self.save(update_fields=['status'])


def refresh_repayment_schedule_statuses(as_of_date=None):
    """Refresh repayment schedule statuses based on due dates and payments."""
    as_of_date = as_of_date or timezone.now().date()

    # Mark fully paid schedules.
    RepaymentSchedule.objects.exclude(
        status=RepaymentStatusChoices.ROLLED_OVER
    ).filter(
        amount_paid__gte=F("amount_due")
    ).update(status=RepaymentStatusChoices.PAID)

    # Mark partial payments (not yet fully paid).
    RepaymentSchedule.objects.exclude(
        status=RepaymentStatusChoices.ROLLED_OVER
    ).filter(
        amount_paid__gt=0,
        amount_paid__lt=F("amount_due")
    ).update(status=RepaymentStatusChoices.PARTIAL)

    # Update zero-paid schedules based on due date.
    zero_paid = RepaymentSchedule.objects.exclude(
        status=RepaymentStatusChoices.ROLLED_OVER
    ).filter(
        amount_paid=0
    )

    zero_paid.filter(
        due_date__lt=as_of_date - timedelta(days=LoanConstants.DEFAULTED_DAYS)
    ).update(status=RepaymentStatusChoices.DEFAULTED)

    zero_paid.filter(
        due_date__lt=as_of_date,
        due_date__gte=as_of_date - timedelta(days=LoanConstants.DEFAULTED_DAYS)
    ).update(status=RepaymentStatusChoices.MISSED)

    zero_paid.filter(due_date=as_of_date).update(status=RepaymentStatusChoices.DUE)
    zero_paid.filter(due_date__gt=as_of_date).update(status=RepaymentStatusChoices.PENDING)



class Repayment(models.Model):
    """Record of a payment made towards a repayment schedule."""
    schedule = models.ForeignKey(
        RepaymentSchedule, on_delete=models.CASCADE, related_name='repayments',
        help_text="The installment this payment is for"
    )
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],  # Must be positive
        help_text="Amount paid (must be positive)"
    )
    payment_date = models.DateField(
        default=timezone.now,
        help_text="Date when payment was received"
    )
    paid_by = models.ForeignKey(
        Borrower, on_delete=models.PROTECT, null=True, blank=True,
        help_text="Borrower who made the payment"
    )
    group_member = models.ForeignKey(
        GroupLoanMember, on_delete=models.PROTECT, null=True, blank=True,
        help_text="Group member if this is for a group loan"
    )
    received_by = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT,
        help_text="Staff member who received the payment"
    )
    status = models.CharField(
        max_length=15, choices=RepaymentStatusChoices.choices, default=RepaymentStatusChoices.PAID,
        help_text="Status of this payment record"
    )
    is_rollover = models.BooleanField(
        default=False,
        help_text="Whether this payment was rolled over from previous period"
    )
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = "Repayment"
        verbose_name_plural = "Repayments"
    
    def __str__(self):
        return f"Payment of {self.amount_paid} on {self.payment_date}"
    
    def clean(self):
        """Validate repayment data before saving."""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate amount_paid does not exceed amount_due
        if self.schedule and self.amount_paid > (self.schedule.amount_due - self.schedule.amount_paid + self.amount_paid):
            # Check overpayment against remaining balance
            remaining = self.schedule.amount_due - self.schedule.amount_paid
            if self.amount_paid > remaining:
                errors['amount_paid'] = f"Payment amount ({self.amount_paid}) cannot exceed remaining balance ({remaining})"
        
        # Validate payment_date is not in the future
        if self.payment_date and self.payment_date > timezone.now().date():
            errors['payment_date'] = "Payment date cannot be in the future"
        
        # Validate amount_paid is positive
        if self.amount_paid and self.amount_paid <= 0:
            errors['amount_paid'] = "Payment amount must be greater than zero"
        
        if errors:
            raise ValidationError(errors)


class LoanPenalty(models.Model):
    """Model for loan penalties."""
    PENALTY_TYPE_CHOICES = [
        ('late_payment', 'Late Payment'),
        ('missed_payment', 'Missed Payment'),
        ('default', 'Default'),
        ('other', 'Other'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='penalties')
    schedule = models.ForeignKey(RepaymentSchedule, on_delete=models.CASCADE, related_name='penalties', null=True, blank=True)
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPE_CHOICES, default='late_payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    applied_date = models.DateField(default=timezone.now)
    cleared_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=PenaltyStatusChoices.choices, default=PenaltyStatusChoices.APPLIED)
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # history = HistoricalRecords()  # Removed for now

    class Meta:
        ordering = ['-applied_date']
        verbose_name_plural = "Loan Penalties"

    def __str__(self):
        return f"Penalty for {self.loan.loan_number} - {self.amount}"


# Keep the old Penalty model for backward compatibility
class Penalty(LoanPenalty):
    """Backward compatibility alias for LoanPenalty."""
    class Meta:
        proxy = True


class WrittenOffLoan(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='written_off')
    written_off_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    written_off_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    # history = HistoricalRecords()  # Removed for now


class MissedPayment(models.Model):
    schedule = models.ForeignKey(RepaymentSchedule, on_delete=models.CASCADE, related_name='missed_payments')
    missed_date = models.DateField(default=timezone.now)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    resolved = models.BooleanField(default=False)
    resolution_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)


class OldLoan(models.Model):
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    group = models.ForeignKey('borrowers.BorrowerGroup', on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    disbursed_date = models.DateField()
    closed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=LoanStatusChoices.choices)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Old Loan for {self.borrower} ({self.disbursed_date})"

@receiver(post_save, sender=RepaymentSchedule)
def apply_penalty_if_missed(sender, instance, **kwargs):
    """Apply penalty for missed payments using atomic get_or_create to prevent duplicate penalties under concurrency."""
    if instance.status == RepaymentStatusChoices.MISSED:
        # Use get_or_create to atomically check and create, preventing duplicate penalties under high concurrency
        penalty_amount = Decimal(str(getattr(settings, 'DEFAULT_MISSED_PAYMENT_PENALTY', '500.00')))
        LoanPenalty.objects.get_or_create(
            schedule=instance,
            defaults={
                'loan': instance.loan,
                'penalty_type': 'missed_payment',
                'amount': penalty_amount,
                'reason': "Auto penalty for missed schedule"
            }
        )


@receiver(post_save, sender=RepaymentSchedule)
def update_loan_npl_classification(sender, instance, created, update_fields, **kwargs):
    """Automatically update loan NPL classification when repayment schedule changes.
    
    Only triggers on meaningful status changes to avoid N+1 updates.
    Skip if NPL flag is disabled for this environment.
    """
    # TEMPORARILY DISABLED - causing 500 errors in arrears view
    # Re-enable after debugging
    return
    
    try:
        # Skip NPL updates if disabled
        if not getattr(settings, 'ENABLE_NPL_AUTO_UPDATE', True):
            return
        
        loan = instance.loan
        if loan.status not in [LoanStatusChoices.DISBURSED, LoanStatusChoices.ACTIVE]:
            return
        
        # Only update on specific field changes
        status_fields = {'status', 'due_date'}
        if update_fields is None:  # If update_fields is None, all fields updated (creation)
            should_update = True
        else:
            should_update = bool(update_fields & status_fields)
        
        if should_update:
            loan.update_npl_classification(save_loan=True)
    except Exception as e:
        # Don't crash - NPL is for reporting, not transaction-critical
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'NPL update error for loan {instance.loan.loan_number}: {str(e)}', exc_info=False)


