from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import AuditModel, LoanStatusChoices, FrequencyChoices
from apps.accounts.models import CustomUser
from apps.borrowers.models import Borrower
# from simple_history.models import HistoricalRecords  # Not needed
import uuid


class InterestTypeChoices(models.TextChoices):
    FLAT = 'flat', 'Flat'
    REDUCING = 'reducing', 'Reducing Balance'
    OTHER = 'other', 'Other'

class RepaymentStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
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
        percentage_fee = loan_amount * (self.processing_fee_percentage / 100)
        return percentage_fee + self.processing_fee_fixed


class LoanQuerySet(models.QuerySet):
    def overdue(self):
        return self.filter(maturity_date__lt=timezone.now().date(),
                           status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED])

    def portfolio_at_risk(self):
        return self.filter(
            repayment_schedules__status__in=[
                RepaymentStatusChoices.MISSED,
                RepaymentStatusChoices.DEFAULTED
            ]
        ).distinct()

    def fully_paid(self):
        return self.filter(outstanding_balance=0)


class LoanManager(models.Manager):
    def get_queryset(self):
        return LoanQuerySet(self.model, using=self._db)

    def overdue(self):
        return self.get_queryset().overdue()

    def portfolio_at_risk(self):
        return self.get_queryset().portfolio_at_risk()

    def fully_paid(self):
        return self.get_queryset().fully_paid()


class Loan(AuditModel):
    loan_number = models.CharField(max_length=20, unique=True, editable=False)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='loans')
    loan_type = models.ForeignKey(LoanType, on_delete=models.PROTECT, related_name='loans', null=True, blank=True)
    
    # Basic loan information
    loan_category = models.CharField(max_length=50, blank=True, null=True)  # New field
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    amount_approved = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    proposed_project = models.CharField(max_length=255, blank=True, null=True)  # New field
    
    # Collateral information
    collateral_name = models.CharField(max_length=255, blank=True, null=True)  # New field
    collateral_worth = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # New field
    collateral_withheld = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # New field
    
    # Payment and disbursement
    repayment_frequency = models.CharField(max_length=15, choices=FrequencyChoices.choices, default=FrequencyChoices.MONTHLY)
    repayment_type = models.CharField(max_length=20, choices=RepaymentTypeChoices.choices, default=RepaymentTypeChoices.MONTHLY)  # New field
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loan_fees_applied = models.BooleanField(default=False)  # New field (for loan_fees radio)
    
    # Disbursement information
    pay_method = models.CharField(max_length=20, choices=PaymentMethodChoices.choices, default=PaymentMethodChoices.CASH)  # New field
    payment_account = models.CharField(max_length=100, blank=True, null=True)  # New field
    loan_officer = models.CharField(max_length=100, blank=True, null=True)  # New field
    start_payment_date = models.DateField(null=True, blank=True)  # New field

    # Dates
    application_date = models.DateField(default=timezone.now)
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)

    # Status and approval
    status = models.CharField(max_length=15, choices=LoanStatusChoices.choices, default=LoanStatusChoices.PENDING)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True, related_name='approved_loans')
    disbursed_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True, related_name='disbursed_loans')

    # Notes and documentation
    application_notes = models.TextField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)  # New field (general notes)
    supporting_document = models.FileField(upload_to='loan_documents/', blank=True, null=True)  # New field

    # Financial calculations
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    objects = LoanManager()
    # history = HistoricalRecords()  # Removed for now

    class Meta:
        ordering = ['-application_date', '-created_at']
        indexes = [
            models.Index(fields=['loan_number']),
            models.Index(fields=['status']),
            models.Index(fields=['borrower']),
            models.Index(fields=['application_date']),
            models.Index(fields=['disbursement_date']),
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
        import random, string
        year = timezone.now().year
        while True:
            number = f"LN{year}{''.join(random.choices(string.digits, k=8))}"
            if not Loan.objects.filter(loan_number=number).exists():
                return number

    def calculate_loan_totals(self):
        if not all([self.amount_approved, self.interest_rate, self.duration_months]):
            return
        principal = Decimal(str(self.amount_approved))
        rate = Decimal(str(self.interest_rate)) / 100
        months = Decimal(str(self.duration_months))

        # Default to flat rate if no loan type or interest type specified
        interest_type = InterestTypeChoices.FLAT
        if self.loan_type and hasattr(self.loan_type, 'interest_type'):
            interest_type = self.loan_type.interest_type

        if interest_type == InterestTypeChoices.REDUCING:
            monthly_rate = rate / 12
            n = months
            emi = principal * (monthly_rate * (1 + monthly_rate)**n) / ((1 + monthly_rate)**n - 1)
            self.total_amount = emi * n
            self.total_interest = self.total_amount - principal
        else:
            self.total_interest = principal * rate * (months / 12)
            self.total_amount = principal + self.total_interest

        self.outstanding_balance = self.total_amount

    def calculate_maturity_date(self):
        from dateutil.relativedelta import relativedelta
        self.maturity_date = self.disbursement_date + relativedelta(months=self.duration_months)

    @property
    def is_overdue(self):
        return self.maturity_date and self.status in [LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED] and timezone.now().date() > self.maturity_date

    @property
    def days_overdue(self):
        return (timezone.now().date() - self.maturity_date).days if self.is_overdue else 0

    def disburse(self, disbursed_by):
        if self.status != LoanStatusChoices.APPROVED:
            raise ValueError("Loan must be approved first")
        self.status = LoanStatusChoices.DISBURSED
        self.disbursed_by = disbursed_by
        self.disbursement_date = timezone.now().date()
        self.save()
        self.generate_repayment_schedule()

    def generate_repayment_schedule(self):
        pass  # to be handled


class GroupLoan(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='group_loan')
    group = models.ForeignKey('borrowers.BorrowerGroup', on_delete=models.PROTECT, related_name='group_loans')

    def __str__(self):
        return f"Group Loan: {self.loan.loan_number} for {self.group.name}"


class GroupLoanMember(models.Model):
    group_loan = models.ForeignKey(GroupLoan, on_delete=models.CASCADE, related_name='members')
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    responsibility_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.borrower.get_full_name()} - {self.responsibility_share}%"


class LoanDisbursement(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='disbursements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    disbursed_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    disbursement_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    is_redisbursed = models.BooleanField(default=False)


class RepaymentSchedule(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayment_schedules')
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=RepaymentStatusChoices.choices, default=RepaymentStatusChoices.PENDING)
    installment_number = models.PositiveIntegerField()
    is_group = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    # history = HistoricalRecords()  # Removed for now

    class Meta:
        ordering = ['loan', 'installment_number']
        unique_together = ['loan', 'installment_number']

    def __str__(self):
        return f"Schedule {self.installment_number} for {self.loan.loan_number}"

    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.status in [RepaymentStatusChoices.MISSED, RepaymentStatusChoices.DEFAULTED]:
            return (timezone.now().date() - self.due_date).days
        return 0


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
