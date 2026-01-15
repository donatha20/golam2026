from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
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


class LoanType(AuditModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    
    default_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    min_duration_months = models.PositiveIntegerField(default=1)
    max_duration_months = models.PositiveIntegerField(default=60)

    interest_type = models.CharField(
        max_length=20,
        choices=InterestTypeChoices.choices,
        default=InterestTypeChoices.FLAT
    )

    requires_savings = models.BooleanField(default=False)
    minimum_savings_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    processing_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    processing_fee_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def calculate_processing_fee(self, loan_amount):
        percentage_fee = Decimal(str(loan_amount)) * (self.processing_fee_percentage / 100)
        return percentage_fee + self.processing_fee_fixed


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
    loan_type = models.ForeignKey(LoanType, on_delete=models.PROTECT, related_name='loans', null=True, blank=True)
    
    # Basic loan information
    loan_category = models.CharField(max_length=50, blank=True, null=True)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    amount_approved = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    proposed_project = models.CharField(max_length=255, blank=True, null=True)
    
    # Collateral information
    collateral_name = models.CharField(max_length=255, blank=True, null=True)
    collateral_worth = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    collateral_withheld = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Payment and disbursement
    repayment_frequency = models.CharField(
        max_length=15, 
        choices=FrequencyChoices.choices, 
        default=FrequencyChoices.MONTHLY
    )
    repayment_type = models.CharField(
        max_length=20, 
        choices=RepaymentTypeChoices.choices, 
        default=RepaymentTypeChoices.MONTHLY
    )
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

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

    def __str__(self):
        return f"{self.loan_number} - {self.borrower.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.loan_number:
            self.loan_number = self.generate_loan_number()
        
        if not self.processing_fee and self.amount_requested and self.loan_type:
            self.processing_fee = self.loan_type.calculate_processing_fee(self.amount_requested)
        
        if self.status == LoanStatusChoices.APPROVED and not self.amount_approved:
            self.amount_approved = self.amount_requested
        
        if self.amount_approved and self.interest_rate and self.duration_months:
            self.calculate_loan_totals()
        
        if self.status == LoanStatusChoices.DISBURSED and self.disbursement_date and not self.maturity_date:
            self.calculate_maturity_date()
        
        super().save(*args, **kwargs)

    def generate_loan_number(self):
        """Generate unique loan number."""
        year = timezone.now().year
        max_attempts = 100
        for _ in range(max_attempts):
            number = f"LN{year}{''.join(random.choices(string.digits, k=8))}"
            if not Loan.objects.filter(loan_number=number).exists():
                return number
        raise ValueError("Unable to generate unique loan number after maximum attempts")

    def calculate_loan_totals(self):
        """Calculate total interest and total amount based on interest type."""
        if not all([self.amount_approved, self.interest_rate, self.duration_months]):
            return
        
        principal = Decimal(str(self.amount_approved))
        rate = Decimal(str(self.interest_rate)) / 100
        months = Decimal(str(self.duration_months))

        # Get interest type from loan type
        interest_type = InterestTypeChoices.FLAT
        if self.loan_type and hasattr(self.loan_type, 'interest_type'):
            interest_type = self.loan_type.interest_type

        if interest_type == InterestTypeChoices.REDUCING:
            # Reducing balance (EMI calculation)
            monthly_rate = rate / 12
            n = months
            if monthly_rate > 0:
                emi = principal * (monthly_rate * (1 + monthly_rate)**n) / ((1 + monthly_rate)**n - 1)
                self.total_amount = emi * n
                self.total_interest = self.total_amount - principal
            else:
                # Zero interest rate
                self.total_amount = principal
                self.total_interest = Decimal('0')
        else:
            # Flat rate
            self.total_interest = principal * rate * (months / 12)
            self.total_amount = principal + self.total_interest

        self.outstanding_balance = self.total_amount

    def calculate_maturity_date(self):
        """Calculate loan maturity date."""
        if self.disbursement_date and self.duration_months:
            self.maturity_date = self.disbursement_date + relativedelta(months=self.duration_months)

    @property
    def oldest_overdue_due_date(self):
        """Returns the due_date of the oldest unpaid overdue installment."""
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
        """Calculate NPL category based on days overdue."""
        days = self.days_overdue
        if days >= 365:
            return NPLCategoryChoices.LOSS
        elif days >= 270:
            return NPLCategoryChoices.DOUBTFUL
        elif days >= 180:
            return NPLCategoryChoices.SUBSTANDARD
        elif days >= 90:
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
        """Recalculate outstanding balance based on payments."""
        total_paid = sum(
            repayment.amount_paid 
            for schedule in self.repayment_schedules.all() 
            for repayment in schedule.repayments.all()
        )
        self.total_paid = total_paid
        self.outstanding_balance = self.total_amount - total_paid
        
        # Update status to closed if fully paid
        if self.outstanding_balance <= 0 and self.status in [
            LoanStatusChoices.ACTIVE, 
            LoanStatusChoices.DISBURSED
        ]:
            self.status = LoanStatusChoices.CLOSED
        
        self.save(update_fields=['outstanding_balance', 'total_paid', 'status'])

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
        """Generate repayment schedule based on loan parameters."""
        if not self.disbursement_date:
            raise ValueError("Disbursement date is required to generate schedule")
        
        # Clear existing schedules
        self.repayment_schedules.all().delete()
        
        # Determine number of installments based on repayment frequency
        frequency_map = {
            FrequencyChoices.DAILY: self.duration_months * 30,
            FrequencyChoices.WEEKLY: self.duration_months * 4,
            FrequencyChoices.MONTHLY: self.duration_months,
            FrequencyChoices.QUARTERLY: max(1, self.duration_months // 3),
        }
        
        num_installments = frequency_map.get(self.repayment_frequency, self.duration_months)
        installment_amount = self.total_amount / num_installments
        
        # Calculate interval
        interval_map = {
            FrequencyChoices.DAILY: timedelta(days=1),
            FrequencyChoices.WEEKLY: timedelta(weeks=1),
            FrequencyChoices.MONTHLY: relativedelta(months=1),
            FrequencyChoices.QUARTERLY: relativedelta(months=3),
        }
        
        start_date = self.start_payment_date or self.disbursement_date
        current_date = start_date
        
        # Create installments
        for i in range(1, num_installments + 1):
            if self.repayment_frequency in [FrequencyChoices.DAILY, FrequencyChoices.WEEKLY]:
                current_date = start_date + (interval_map[self.repayment_frequency] * i)
            else:
                current_date = start_date + (interval_map[self.repayment_frequency] * i)
            
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
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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
        """Update schedule status based on payments."""
        today = timezone.now().date()
        
        if self.amount_paid >= self.amount_due:
            self.status = RepaymentStatusChoices.PAID
        elif self.amount_paid > 0:
            self.status = RepaymentStatusChoices.PARTIAL
        elif self.due_date < today:
            # Overdue logic
            days_overdue = (today - self.due_date).days
            if days_overdue > 30:
                self.status = RepaymentStatusChoices.DEFAULTED
            else:
                self.status = RepaymentStatusChoices.MISSED
        elif self.due_date == today:
            self.status = RepaymentStatusChoices.DUE
        else:
            self.status = RepaymentStatusChoices.PENDING
        
        self.save(update_fields=['status'])



class Repayment(models.Model):
    schedule = models.ForeignKey(RepaymentSchedule, on_delete=models.CASCADE, related_name='repayments')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    paid_by = models.ForeignKey(Borrower, on_delete=models.PROTECT, null=True, blank=True)
    group_member = models.ForeignKey(GroupLoanMember, on_delete=models.PROTECT, null=True, blank=True)
    received_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    status = models.CharField(max_length=15, choices=RepaymentStatusChoices.choices, default=RepaymentStatusChoices.PAID)
    is_rollover = models.BooleanField(default=False)
    # history = HistoricalRecords()  # Removed for now


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
    if instance.status == RepaymentStatusChoices.MISSED:
        if not LoanPenalty.objects.filter(schedule=instance).exists():
            LoanPenalty.objects.create(
                loan=instance.loan,
                schedule=instance,
                penalty_type='missed_payment',
                amount=Decimal('500.00'),  # You can use a dynamic logic
                reason="Auto penalty for missed schedule"
            )
