"""
Repayment and payment processing models for the microfinance system.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q
from decimal import Decimal
from apps.core.models import AuditModel, PaymentMethodChoices
from apps.accounts.models import CustomUser
from apps.borrowers.models import Borrower
from apps.loans.models import Loan


class PaymentStatus(models.TextChoices):
    """Payment status choices."""
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    REVERSED = 'reversed', 'Reversed'


class LoanRepaymentSchedule(AuditModel):
    """
    Enhanced loan repayment schedule model - amortization table.
    """
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='repayment_schedule'
    )
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()

    # Original scheduled amounts
    scheduled_principal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Original scheduled principal amount"
    )
    scheduled_interest = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Original scheduled interest amount"
    )
    scheduled_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Original scheduled total amount"
    )

    # Current amounts (may differ from scheduled due to adjustments)
    principal_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current principal amount due"
    )
    interest_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current interest amount due"
    )
    penalty_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Penalty amount for late payment"
    )
    fees_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Additional fees amount"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount due for this installment"
    )

    # Balance tracking
    opening_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Outstanding balance at start of period"
    )
    closing_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Outstanding balance at end of period"
    )

    # Payment tracking
    principal_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Principal amount paid"
    )
    interest_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Interest amount paid"
    )
    penalty_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Penalty amount paid"
    )
    fees_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fees amount paid"
    )
    total_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount paid for this installment"
    )

    # Status tracking
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('partial', 'Partially Paid'),
            ('paid', 'Fully Paid'),
            ('overdue', 'Overdue'),
            ('written_off', 'Written Off'),
        ],
        default='pending'
    )
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)

    # Additional tracking
    days_overdue = models.PositiveIntegerField(default=0)
    last_payment_date = models.DateField(null=True, blank=True)
    penalty_calculation_date = models.DateField(null=True, blank=True)

    # Adjustment tracking
    is_adjusted = models.BooleanField(default=False)
    adjustment_reason = models.TextField(blank=True, null=True)
    adjusted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_adjustments'
    )
    adjustment_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['loan', 'installment_number']
        unique_together = ['loan', 'installment_number']
        indexes = [
            models.Index(fields=['loan', 'due_date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['is_paid']),
        ]

    def __str__(self):
        return f"{self.loan.loan_number} - Installment {self.installment_number}"

    def save(self, *args, **kwargs):
        # Update total amount
        self.total_amount = (
            self.principal_amount + self.interest_amount +
            self.penalty_amount + self.fees_amount
        )

        # Update total paid
        self.total_paid = (
            self.principal_paid + self.interest_paid +
            self.penalty_paid + self.fees_paid
        )

        # Update payment status
        self.update_payment_status()

        # Update days overdue
        if not self.is_paid and timezone.now().date() > self.due_date:
            self.days_overdue = (timezone.now().date() - self.due_date).days
            self.payment_status = 'overdue'

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if this installment is overdue."""
        return not self.is_paid and timezone.now().date() > self.due_date

    @property
    def outstanding_amount(self):
        """Calculate outstanding amount for this installment."""
        return self.total_amount - self.total_paid

    @property
    def outstanding_principal(self):
        """Calculate outstanding principal for this installment."""
        return self.principal_amount - self.principal_paid

    @property
    def outstanding_interest(self):
        """Calculate outstanding interest for this installment."""
        return self.interest_amount - self.interest_paid

    @property
    def outstanding_penalty(self):
        """Calculate outstanding penalty for this installment."""
        return self.penalty_amount - self.penalty_paid

    @property
    def outstanding_fees(self):
        """Calculate outstanding fees for this installment."""
        return self.fees_amount - self.fees_paid

    @property
    def payment_percentage(self):
        """Calculate payment completion percentage."""
        if self.total_amount > 0:
            return (self.total_paid / self.total_amount) * 100
        return 0

    def update_payment_status(self):
        """Update payment status based on amounts paid."""
        if self.total_paid >= self.total_amount:
            self.payment_status = 'paid'
            self.is_paid = True
            if not self.paid_date:
                self.paid_date = timezone.now().date()
        elif self.total_paid > 0:
            self.payment_status = 'partial'
            self.is_paid = False
        else:
            if timezone.now().date() > self.due_date:
                self.payment_status = 'overdue'
            else:
                self.payment_status = 'pending'
            self.is_paid = False

    def calculate_penalty(self, penalty_configuration=None):
        """Calculate penalty for overdue payment using penalty configuration."""
        if not self.is_overdue:
            return Decimal('0.00')

        # Use penalty configuration from loan type or default
        if penalty_configuration:
            penalty_rate = penalty_configuration.penalty_rate
            penalty_type = penalty_configuration.penalty_type
            grace_period = penalty_configuration.grace_period_days
            max_penalty = penalty_configuration.max_penalty_amount
        else:
            # Default penalty calculation
            penalty_rate = Decimal('0.01')  # 1% per day
            penalty_type = 'daily'
            grace_period = 0
            max_penalty = None

        # Apply grace period
        effective_days_overdue = max(0, self.days_overdue - grace_period)

        if effective_days_overdue <= 0:
            return Decimal('0.00')

        # Calculate penalty based on type
        if penalty_type == 'fixed':
            penalty = penalty_rate
        elif penalty_type == 'percentage':
            penalty = self.outstanding_amount * (penalty_rate / 100)
        elif penalty_type == 'daily':
            penalty = self.outstanding_amount * (penalty_rate / 100) * effective_days_overdue
        elif penalty_type == 'compound':
            # Compound penalty calculation
            penalty = self.outstanding_amount * (
                (1 + penalty_rate / 100) ** effective_days_overdue - 1
            )
        else:
            penalty = Decimal('0.00')

        # Apply maximum penalty limit
        if max_penalty and penalty > max_penalty:
            penalty = max_penalty

        return penalty

    def apply_penalty(self, penalty_configuration=None):
        """Apply penalty to this installment."""
        penalty = self.calculate_penalty(penalty_configuration)
        if penalty > 0:
            self.penalty_amount = penalty
            self.penalty_calculation_date = timezone.now().date()
            self.save()
        return penalty

    def allocate_payment(self, payment_amount):
        """Allocate payment amount to this installment."""
        remaining_amount = Decimal(str(payment_amount))
        allocation = {
            'penalty': Decimal('0.00'),
            'interest': Decimal('0.00'),
            'principal': Decimal('0.00'),
            'fees': Decimal('0.00'),
            'excess': Decimal('0.00')
        }

        # Payment allocation priority: Penalty -> Interest -> Principal -> Fees

        # 1. Pay penalty first
        penalty_due = self.outstanding_penalty
        if penalty_due > 0 and remaining_amount > 0:
            penalty_payment = min(remaining_amount, penalty_due)
            allocation['penalty'] = penalty_payment
            self.penalty_paid += penalty_payment
            remaining_amount -= penalty_payment

        # 2. Pay interest
        interest_due = self.outstanding_interest
        if interest_due > 0 and remaining_amount > 0:
            interest_payment = min(remaining_amount, interest_due)
            allocation['interest'] = interest_payment
            self.interest_paid += interest_payment
            remaining_amount -= interest_payment

        # 3. Pay principal
        principal_due = self.outstanding_principal
        if principal_due > 0 and remaining_amount > 0:
            principal_payment = min(remaining_amount, principal_due)
            allocation['principal'] = principal_payment
            self.principal_paid += principal_payment
            remaining_amount -= principal_payment

        # 4. Pay fees
        fees_due = self.outstanding_fees
        if fees_due > 0 and remaining_amount > 0:
            fees_payment = min(remaining_amount, fees_due)
            allocation['fees'] = fees_payment
            self.fees_paid += fees_payment
            remaining_amount -= fees_payment

        # 5. Any excess amount
        if remaining_amount > 0:
            allocation['excess'] = remaining_amount

        # Update last payment date
        self.last_payment_date = timezone.now().date()

        # Save changes
        self.save()

        return allocation


class Payment(AuditModel):
    """
    Enhanced payment model to track all payments made by borrowers.
    """
    # System generated fields
    payment_reference = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated payment reference number"
    )

    # Payment details
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    borrower = models.ForeignKey(
        Borrower,
        on_delete=models.PROTECT,
        related_name='payments'
    )

    # Amount and method
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total payment amount"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethodChoices.choices,
        default=PaymentMethodChoices.CASH
    )

    # Payment processing
    payment_date = models.DateField(default=timezone.now)
    processed_date = models.DateTimeField(auto_now_add=True)
    collected_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='collected_payments'
    )

    # Status and verification
    status = models.CharField(
        max_length=15,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    # Additional details
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Allocation breakdown
    principal_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Principal amount paid"
    )
    interest_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Interest amount paid"
    )
    penalty_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Penalty amount paid"
    )
    fees_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fees amount paid"
    )
    advance_payment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Advance payment amount"
    )

    # Payment type classification
    payment_type = models.CharField(
        max_length=20,
        choices=[
            ('regular', 'Regular Payment'),
            ('partial', 'Partial Payment'),
            ('advance', 'Advance Payment'),
            ('penalty', 'Penalty Payment'),
            ('settlement', 'Full Settlement'),
            ('adjustment', 'Payment Adjustment'),
        ],
        default='regular'
    )

    # Verification and approval
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True)

    # Reversal tracking
    is_reversed = models.BooleanField(default=False)
    reversed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversed_payments'
    )
    reversal_date = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True, null=True)
    original_payment = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversal_payments'
    )

    # Balance tracking
    loan_balance_before = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Loan balance before this payment"
    )
    loan_balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Loan balance after this payment"
    )

    class Meta:
        ordering = ['-payment_date', '-processed_date']
        indexes = [
            models.Index(fields=['payment_reference']),
            models.Index(fields=['loan']),
            models.Index(fields=['borrower']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['collected_by']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.payment_reference} - {self.borrower.get_full_name()} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = self.generate_payment_reference()
        
        # Allocate payment if not already done
        if not any([self.principal_paid, self.interest_paid, self.penalty_paid, self.fees_paid]):
            self.allocate_payment()
        
        super().save(*args, **kwargs)
        
        # Update loan balance after payment
        if self.status == PaymentStatus.COMPLETED:
            self.update_loan_balance()

    def generate_payment_reference(self):
        """Generate a unique payment reference."""
        import random
        import string
        
        # Format: PAY + Year + Month + 6 random digits
        now = timezone.now()
        year_month = f"{now.year}{now.month:02d}"
        random_part = ''.join(random.choices(string.digits, k=6))
        payment_ref = f"PAY{year_month}{random_part}"
        
        # Ensure uniqueness
        while Payment.objects.filter(payment_reference=payment_ref).exists():
            random_part = ''.join(random.choices(string.digits, k=6))
            payment_ref = f"PAY{year_month}{random_part}"
        
        return payment_ref

    def allocate_payment(self):
        """Allocate payment amount to principal, interest, penalty, and fees."""
        remaining_amount = Decimal(str(self.amount))
        
        # Get overdue installments first
        overdue_installments = self.loan.repayment_schedule.filter(
            is_paid=False,
            due_date__lt=timezone.now().date()
        ).order_by('due_date')
        
        # Get current installments
        current_installments = self.loan.repayment_schedule.filter(
            is_paid=False,
            due_date__gte=timezone.now().date()
        ).order_by('due_date')
        
        # Combine overdue and current installments
        installments = list(overdue_installments) + list(current_installments)
        
        # Allocation priority: Penalty -> Interest -> Principal -> Fees
        for installment in installments:
            if remaining_amount <= 0:
                break
            
            # Pay penalty first
            if installment.penalty_amount > 0 and remaining_amount > 0:
                penalty_to_pay = min(remaining_amount, installment.penalty_amount)
                self.penalty_paid += penalty_to_pay
                remaining_amount -= penalty_to_pay
            
            # Pay interest
            if installment.interest_amount > 0 and remaining_amount > 0:
                interest_to_pay = min(remaining_amount, installment.interest_amount)
                self.interest_paid += interest_to_pay
                remaining_amount -= interest_to_pay
            
            # Pay principal
            if installment.principal_amount > 0 and remaining_amount > 0:
                principal_to_pay = min(remaining_amount, installment.principal_amount)
                self.principal_paid += principal_to_pay
                remaining_amount -= principal_to_pay
        
        # Any remaining amount goes to fees or advance payment
        if remaining_amount > 0:
            self.fees_paid = remaining_amount

    def update_loan_balance(self):
        """Update loan outstanding balance after payment."""
        if self.loan:
            self.loan.outstanding_balance -= self.amount
            if self.loan.outstanding_balance < 0:
                self.loan.outstanding_balance = 0
            self.loan.save()
    
    @property
    def total_allocated(self):
        """Get total amount allocated from this payment."""
        return self.principal_paid + self.interest_paid + self.penalty_paid + self.fees_paid
    
    @property
    def unallocated_amount(self):
        """Get amount not yet allocated."""
        return self.amount - self.total_allocated
    
    @property
    def is_fully_allocated(self):
        """Check if payment is fully allocated."""
        return self.unallocated_amount <= Decimal('0.01')  # Allow small rounding differences


class DailyCollection(AuditModel):
    """
    Enhanced daily collection summary model with comprehensive tracking.
    """
    collection_date = models.DateField()
    collector = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='daily_collections'
    )

    # Collection targets and goals
    target_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Target collection amount for the day"
    )
    target_payments = models.PositiveIntegerField(
        default=0,
        help_text="Target number of payments for the day"
    )

    # Actual collection summary
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount collected"
    )
    payment_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of payments collected"
    )
    borrower_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique borrowers who made payments"
    )

    # Payment method breakdown
    cash_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount collected in cash"
    )
    cash_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of cash payments"
    )
    digital_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount collected through digital methods"
    )
    digital_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of digital payments"
    )
    bank_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount collected through bank transfers"
    )
    bank_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of bank transfer payments"
    )

    # Collection type breakdown
    regular_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount from regular scheduled payments"
    )
    overdue_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount from overdue payments"
    )
    advance_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount from advance payments"
    )
    penalty_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount collected as penalties"
    )

    # Performance metrics
    collection_efficiency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Collection efficiency percentage (actual vs target)"
    )
    average_payment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Average payment amount"
    )

    # Validation and approval
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Validation'),
            ('validated', 'Validated'),
            ('discrepancy', 'Has Discrepancy'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_collections'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True)

    # Discrepancy tracking
    has_discrepancy = models.BooleanField(default=False)
    discrepancy_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount of discrepancy (if any)"
    )
    discrepancy_reason = models.TextField(blank=True, null=True)
    discrepancy_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_discrepancies'
    )
    resolution_date = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)

    # Additional tracking
    collection_start_time = models.TimeField(null=True, blank=True)
    collection_end_time = models.TimeField(null=True, blank=True)
    collection_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Duration of collection activity in hours"
    )

    # Location and route information
    collection_route = models.CharField(max_length=100, blank=True, null=True)
    collection_area = models.CharField(max_length=100, blank=True, null=True)
    travel_distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance traveled for collections in kilometers"
    )

    # Notes and comments
    notes = models.TextField(blank=True, null=True)
    supervisor_comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-collection_date', 'collector']
        unique_together = ['collection_date', 'collector']
        indexes = [
            models.Index(fields=['collection_date', 'collector']),
            models.Index(fields=['validation_status']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return f"Collection {self.collection_date} - {self.collector.get_full_name()}"

    def save(self, *args, **kwargs):
        # Calculate collection efficiency
        if self.target_amount > 0:
            self.collection_efficiency = (self.total_amount / self.target_amount) * 100
        else:
            self.collection_efficiency = Decimal('0.00')

        # Calculate average payment
        if self.payment_count > 0:
            self.average_payment = self.total_amount / self.payment_count
        else:
            self.average_payment = Decimal('0.00')

        # Calculate collection duration
        if self.collection_start_time and self.collection_end_time:
            start_minutes = self.collection_start_time.hour * 60 + self.collection_start_time.minute
            end_minutes = self.collection_end_time.hour * 60 + self.collection_end_time.minute
            duration_minutes = end_minutes - start_minutes
            if duration_minutes < 0:  # Handle next day scenario
                duration_minutes += 24 * 60
            self.collection_duration_hours = Decimal(str(duration_minutes / 60))

        super().save(*args, **kwargs)

    @property
    def target_achievement_percentage(self):
        """Calculate target achievement percentage."""
        if self.target_amount > 0:
            return (self.total_amount / self.target_amount) * 100
        return Decimal('0.00')

    @property
    def variance_amount(self):
        """Calculate variance from target."""
        return self.total_amount - self.target_amount

    @property
    def is_target_achieved(self):
        """Check if target is achieved."""
        return self.total_amount >= self.target_amount

    @property
    def collection_rate_per_hour(self):
        """Calculate collection rate per hour."""
        if self.collection_duration_hours and self.collection_duration_hours > 0:
            return self.total_amount / self.collection_duration_hours
        return Decimal('0.00')

    @property
    def payments_per_hour(self):
        """Calculate payments processed per hour."""
        if self.collection_duration_hours and self.collection_duration_hours > 0:
            return self.payment_count / float(self.collection_duration_hours)
        return 0

    def calculate_totals_from_payments(self):
        """Calculate and update collection totals from actual payments."""
        payments = Payment.objects.filter(
            payment_date=self.collection_date,
            collected_by=self.collector,
            status=PaymentStatus.COMPLETED
        )

        # Reset all totals
        self.total_amount = Decimal('0.00')
        self.payment_count = 0
        self.borrower_count = 0
        self.cash_amount = Decimal('0.00')
        self.cash_count = 0
        self.digital_amount = Decimal('0.00')
        self.digital_count = 0
        self.bank_amount = Decimal('0.00')
        self.bank_count = 0
        self.regular_amount = Decimal('0.00')
        self.overdue_amount = Decimal('0.00')
        self.advance_amount = Decimal('0.00')
        self.penalty_amount = Decimal('0.00')

        # Calculate totals
        for payment in payments:
            self.total_amount += payment.amount
            self.payment_count += 1

            # Payment method breakdown
            if payment.payment_method == 'cash':
                self.cash_amount += payment.amount
                self.cash_count += 1
            elif payment.payment_method in ['mobile_money', 'card', 'online']:
                self.digital_amount += payment.amount
                self.digital_count += 1
            elif payment.payment_method == 'bank_transfer':
                self.bank_amount += payment.amount
                self.bank_count += 1

            # Payment type breakdown
            if payment.payment_type == 'regular':
                self.regular_amount += payment.amount
            elif payment.payment_type == 'advance':
                self.advance_amount += payment.amount
            elif payment.payment_type == 'penalty':
                self.penalty_amount += payment.amount

            # Add penalty amounts
            self.penalty_amount += payment.penalty_paid

        # Calculate unique borrowers
        self.borrower_count = payments.values('borrower').distinct().count()

        # Identify overdue payments (payments for overdue installments)
        overdue_payments = payments.filter(
            loan__repayment_schedule__payment_status='overdue',
            loan__repayment_schedule__due_date__lt=self.collection_date
        ).distinct()

        for payment in overdue_payments:
            self.overdue_amount += payment.amount

        self.save()

    def validate_collection(self):
        """Validate collection against actual payments and identify discrepancies."""
        # Recalculate totals from payments
        calculated_totals = self.get_calculated_totals()

        # Check for discrepancies
        amount_discrepancy = abs(self.total_amount - calculated_totals['total_amount'])
        count_discrepancy = abs(self.payment_count - calculated_totals['payment_count'])

        tolerance = Decimal('0.01')  # 1 paisa tolerance

        if amount_discrepancy > tolerance or count_discrepancy > 0:
            self.has_discrepancy = True
            self.discrepancy_amount = amount_discrepancy
            self.discrepancy_reason = f"Amount variance: ₹{amount_discrepancy}, Count variance: {count_discrepancy}"
            self.validation_status = 'discrepancy'
        else:
            self.has_discrepancy = False
            self.discrepancy_amount = Decimal('0.00')
            self.discrepancy_reason = None
            self.validation_status = 'validated'

        self.save()
        return not self.has_discrepancy

    def get_calculated_totals(self):
        """Get calculated totals from actual payments for comparison."""
        payments = Payment.objects.filter(
            payment_date=self.collection_date,
            collected_by=self.collector,
            status=PaymentStatus.COMPLETED
        )

        return {
            'total_amount': payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'payment_count': payments.count(),
            'borrower_count': payments.values('borrower').distinct().count(),
            'cash_amount': payments.filter(payment_method='cash').aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'digital_amount': payments.filter(payment_method__in=['mobile_money', 'card', 'online']).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'bank_amount': payments.filter(payment_method='bank_transfer').aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        }

    def approve_collection(self, approved_by, notes=None):
        """Approve the collection after validation."""
        self.validation_status = 'approved'
        self.is_verified = True
        self.verified_by = approved_by
        self.verification_date = timezone.now()
        if notes:
            self.verification_notes = notes

        self.save()

    def reject_collection(self, rejected_by, reason):
        """Reject the collection with reason."""
        self.validation_status = 'rejected'
        self.is_verified = False
        self.verified_by = rejected_by
        self.verification_date = timezone.now()
        self.verification_notes = reason

        self.save()

    def resolve_discrepancy(self, resolved_by, resolution_notes):
        """Resolve collection discrepancy."""
        if not self.has_discrepancy:
            raise ValueError("No discrepancy to resolve")

        self.discrepancy_resolved = True
        self.resolved_by = resolved_by
        self.resolution_date = timezone.now()
        self.resolution_notes = resolution_notes
        self.validation_status = 'validated'

        self.save()


class CollectionSummary(models.Model):
    """
    Daily collection summary aggregated across all collectors.
    """
    summary_date = models.DateField(unique=True)

    # Aggregate totals
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount collected across all collectors"
    )
    total_payments = models.PositiveIntegerField(
        default=0,
        help_text="Total number of payments across all collectors"
    )
    total_borrowers = models.PositiveIntegerField(
        default=0,
        help_text="Total unique borrowers who made payments"
    )
    active_collectors = models.PositiveIntegerField(
        default=0,
        help_text="Number of collectors who made collections"
    )

    # Target vs actual
    total_target = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total target amount across all collectors"
    )
    achievement_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overall achievement percentage"
    )

    # Payment method breakdown
    cash_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    digital_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    bank_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Collection type breakdown
    regular_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    overdue_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    advance_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    penalty_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Validation status
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Validation'),
            ('validated', 'Validated'),
            ('discrepancy', 'Has Discrepancies'),
            ('approved', 'Approved'),
        ],
        default='pending'
    )

    # Discrepancy tracking
    collections_with_discrepancy = models.PositiveIntegerField(
        default=0,
        help_text="Number of individual collections with discrepancies"
    )
    total_discrepancy_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total discrepancy amount across all collections"
    )

    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_summaries'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-summary_date']
        verbose_name_plural = "Collection Summaries"

    def __str__(self):
        return f"Collection Summary - {self.summary_date}"

    def generate_summary(self):
        """Generate summary from individual daily collections."""
        collections = DailyCollection.objects.filter(collection_date=self.summary_date)

        # Reset totals
        self.total_amount = Decimal('0.00')
        self.total_payments = 0
        self.total_borrowers = 0
        self.active_collectors = 0
        self.total_target = Decimal('0.00')
        self.cash_total = Decimal('0.00')
        self.digital_total = Decimal('0.00')
        self.bank_total = Decimal('0.00')
        self.regular_total = Decimal('0.00')
        self.overdue_total = Decimal('0.00')
        self.advance_total = Decimal('0.00')
        self.penalty_total = Decimal('0.00')
        self.collections_with_discrepancy = 0
        self.total_discrepancy_amount = Decimal('0.00')

        # Aggregate data
        for collection in collections:
            self.total_amount += collection.total_amount
            self.total_payments += collection.payment_count
            self.total_target += collection.target_amount
            self.cash_total += collection.cash_amount
            self.digital_total += collection.digital_amount
            self.bank_total += collection.bank_amount
            self.regular_total += collection.regular_amount
            self.overdue_total += collection.overdue_amount
            self.advance_total += collection.advance_amount
            self.penalty_total += collection.penalty_amount

            if collection.has_discrepancy:
                self.collections_with_discrepancy += 1
                self.total_discrepancy_amount += collection.discrepancy_amount

        # Calculate unique borrowers across all collectors
        all_payments = Payment.objects.filter(
            payment_date=self.summary_date,
            status=PaymentStatus.COMPLETED
        )
        self.total_borrowers = all_payments.values('borrower').distinct().count()

        # Count active collectors
        self.active_collectors = collections.count()

        # Calculate achievement percentage
        if self.total_target > 0:
            self.achievement_percentage = (self.total_amount / self.total_target) * 100
        else:
            self.achievement_percentage = Decimal('0.00')

        # Determine validation status
        if self.collections_with_discrepancy > 0:
            self.validation_status = 'discrepancy'
        else:
            self.validation_status = 'validated'

        self.save()

    def approve_summary(self, approved_by, notes=None):
        """Approve the collection summary."""
        if self.validation_status == 'discrepancy':
            raise ValueError("Cannot approve summary with discrepancies")

        self.is_approved = True
        self.approved_by = approved_by
        self.approval_date = timezone.now()
        if notes:
            self.approval_notes = notes
        self.validation_status = 'approved'

        self.save()


class PaymentAllocation(models.Model):
    """Track detailed payment allocation to specific installments."""

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    installment = models.ForeignKey(
        LoanRepaymentSchedule,
        on_delete=models.CASCADE,
        related_name='payment_allocations'
    )

    # Allocation amounts
    principal_allocated = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    interest_allocated = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    penalty_allocated = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    fees_allocated = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_allocated = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Tracking
    allocation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['installment__installment_number']
        unique_together = ['payment', 'installment']

    def __str__(self):
        return f"{self.payment.payment_reference} -> Installment {self.installment.installment_number}"

    def save(self, *args, **kwargs):
        self.total_allocated = (
            self.principal_allocated + self.interest_allocated +
            self.penalty_allocated + self.fees_allocated
        )
        super().save(*args, **kwargs)


class PaymentHistory(models.Model):
    """Track payment history and changes for audit purposes."""

    ACTION_TYPES = [
        ('created', 'Payment Created'),
        ('processed', 'Payment Processed'),
        ('verified', 'Payment Verified'),
        ('reversed', 'Payment Reversed'),
        ('adjusted', 'Payment Adjusted'),
        ('cancelled', 'Payment Cancelled'),
    ]

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    action_date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payment_actions'
    )

    # Change tracking
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-action_date']

    def __str__(self):
        return f"{self.payment.payment_reference} - {self.get_action_type_display()}"


class OutstandingBalance(models.Model):
    """Track outstanding balances for loans with historical data."""

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='balance_history'
    )

    # Balance components
    principal_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    interest_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    penalty_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    fees_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Tracking
    balance_date = models.DateField()
    last_payment_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)

    # Status
    is_current = models.BooleanField(default=True)
    days_overdue = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-balance_date']
        unique_together = ['loan', 'balance_date']

    def __str__(self):
        return f"{self.loan.loan_number} - {self.balance_date} - ₹{self.total_outstanding}"

    def save(self, *args, **kwargs):
        self.total_outstanding = (
            self.principal_outstanding + self.interest_outstanding +
            self.penalty_outstanding + self.fees_outstanding
        )
        super().save(*args, **kwargs)
