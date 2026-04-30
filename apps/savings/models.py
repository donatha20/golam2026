"""
Savings management models for the microfinance system.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from apps.core.models import AuditModel, StatusChoices, TransactionTypeChoices
from apps.accounts.models import CustomUser
from apps.borrowers.models import Borrower


class SavingsCategory(models.Model):
    """Savings product categories."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=20, unique=True)
    
    # Category settings
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_savings_categories'
    )
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'Savings Categories'
    
    def __str__(self):
        return self.name


class SavingsCharge(models.Model):
    """Savings charges and fees configuration."""
    
    CHARGE_TYPES = [
        ('withdrawal', 'Withdrawal Charge'),
        ('service', 'Service Charge'),
        ('maintenance', 'Maintenance Fee'),
        ('penalty', 'Penalty Fee'),
        ('processing', 'Processing Fee'),
        ('statement', 'Statement Fee'),
        ('card', 'Card Fee'),
        ('other', 'Other Charge'),
    ]
    
    CALCULATION_METHODS = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Amount'),
        ('tier', 'Tiered Charges'),
        ('minimum', 'Minimum Amount'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    charge_type = models.CharField(max_length=20, choices=CHARGE_TYPES)
    calculation_method = models.CharField(max_length=20, choices=CALCULATION_METHODS, default='fixed')
    
    # Charge amounts
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    percentage_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    maximum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Applicability
    applies_to_all_products = models.BooleanField(default=True)
    applicable_products = models.ManyToManyField(
        'SavingsProduct',
        blank=True,
        related_name='specific_charges'
    )
    
    # Frequency and timing
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('per_transaction', 'Per Transaction'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
            ('one_time', 'One Time'),
        ],
        default='per_transaction'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_savings_charges'
    )
    
    class Meta:
        ordering = ['charge_type', 'name']
    
    def __str__(self):
        return f"{self.get_charge_type_display()} - {self.name}"
    
    def calculate_charge(self, amount):
        """Calculate charge amount based on transaction amount."""
        if not self.is_active:
            return Decimal('0.00')
        
        if self.calculation_method == 'fixed':
            return self.fixed_amount
        elif self.calculation_method == 'percentage':
            charge = amount * (self.percentage_rate / 100)
        elif self.calculation_method == 'minimum':
            charge = max(self.minimum_amount, amount * (self.percentage_rate / 100))
        else:
            charge = amount * (self.percentage_rate / 100)
        
        # Apply maximum limit if set
        if self.maximum_amount:
            charge = min(charge, self.maximum_amount)
        
        # Apply minimum amount
        if self.minimum_amount:
            charge = max(charge, self.minimum_amount)
        
        return charge


class SavingsProduct(models.Model):
    """Savings product configuration."""

    INTEREST_CALCULATION_METHODS = [
        ('simple', 'Simple Interest'),
        ('compound_monthly', 'Compound Monthly'),
        ('compound_quarterly', 'Compound Quarterly'),
        ('compound_annually', 'Compound Annually'),
    ]

    INTEREST_POSTING_FREQUENCY = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annually', 'Semi-Annually'),
        ('annually', 'Annually'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        SavingsCategory,
        on_delete=models.PROTECT,
        related_name='products',
        null=True,
        blank=True
    )

    # Interest settings
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('50.00'))],
        help_text="Annual interest rate as percentage"
    )
    interest_calculation_method = models.CharField(
        max_length=20,
        choices=INTEREST_CALCULATION_METHODS,
        default='simple'
    )
    interest_posting_frequency = models.CharField(
        max_length=15,
        choices=INTEREST_POSTING_FREQUENCY,
        default='monthly'
    )

    # Balance requirements
    minimum_opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    minimum_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    maximum_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Transaction limits
    minimum_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    maximum_deposit_per_day = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    minimum_withdrawal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    maximum_withdrawal_per_day = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Fees
    account_maintenance_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    withdrawal_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Status and settings
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    allow_overdraft = models.BooleanField(default=False)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SavingsLoanRule(models.Model):
    """Rules linking savings requirements to loan categories."""

    RULE_TYPES = [
        ('minimum_balance', 'Minimum Balance Required'),
        ('savings_period', 'Minimum Savings Period'),
        ('savings_ratio', 'Savings to Loan Ratio'),
        ('mandatory_savings', 'Mandatory Savings Before Loan'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)

    # Loan category reference (we'll use CharField to avoid circular imports)
    loan_category = models.CharField(max_length=50, help_text="Loan category this rule applies to")

    # Rule parameters
    minimum_balance_required = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    minimum_savings_period_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum months of savings history required"
    )
    savings_to_loan_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
        help_text="Required savings as percentage of loan amount"
    )
    mandatory_savings_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Rule settings
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=True)
    grace_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Grace period for rule compliance"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['loan_category', 'rule_type']
        unique_together = ['loan_category', 'rule_type']

    def __str__(self):
        return f"{self.loan_category} - {self.get_rule_type_display()}"

    def check_compliance(self, savings_account, loan_amount=None):
        """Check if savings account complies with this rule."""
        if not self.is_active:
            return True, "Rule is not active"

        if self.rule_type == 'minimum_balance':
            if savings_account.balance >= self.minimum_balance_required:
                return True, "Minimum balance requirement met"
            else:
                return False, f"Minimum balance of Tsh {self.minimum_balance_required} required. Current balance: Tsh {savings_account.balance}"

        elif self.rule_type == 'savings_period':
            account_age_months = (timezone.now().date() - savings_account.opened_date).days / 30.44
            if account_age_months >= self.minimum_savings_period_months:
                return True, "Minimum savings period requirement met"
            else:
                return False, f"Minimum savings period of {self.minimum_savings_period_months} months required. Account age: {account_age_months:.1f} months"

        elif self.rule_type == 'savings_ratio' and loan_amount:
            required_savings = loan_amount * (self.savings_to_loan_ratio / 100)
            if savings_account.balance >= required_savings:
                return True, "Savings to loan ratio requirement met"
            else:
                return False, f"Savings of Tsh {required_savings} required for loan of Tsh {loan_amount}. Current savings: Tsh {savings_account.balance}"

        elif self.rule_type == 'mandatory_savings':
            if savings_account.balance >= self.mandatory_savings_amount:
                return True, "Mandatory savings requirement met"
            else:
                return False, f"Mandatory savings of Tsh {self.mandatory_savings_amount} required. Current savings: Tsh {savings_account.balance}"

        return True, "Rule check passed"


class SavingsAccountStatus(models.TextChoices):
    """Savings account status choices."""
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    CLOSED = 'closed', 'Closed'
    SUSPENDED = 'suspended', 'Suspended'


class SavingsAccount(AuditModel):
    """
    Enhanced savings account model for borrowers.
    """
    account_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated account number"
    )
    borrower = models.ForeignKey(
        Borrower,
        on_delete=models.PROTECT,
        related_name='savings_accounts'
    )
    savings_product = models.ForeignKey(
        SavingsProduct,
        on_delete=models.PROTECT,
        related_name='accounts',
        null=True,
        blank=True,
        help_text="Savings product type for this account"
    )

    # Balance and limits
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    available_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Balance available for withdrawal (excluding holds)"
    )

    # Interest tracking
    accrued_interest = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    last_interest_calculation = models.DateField(null=True, blank=True)
    last_interest_posting = models.DateField(null=True, blank=True)
    total_interest_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Account details
    status = models.CharField(
        max_length=15,
        choices=SavingsAccountStatus.choices,
        default=SavingsAccountStatus.ACTIVE
    )
    opened_date = models.DateField(default=timezone.now)
    opened_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='opened_savings_accounts'
    )
    closed_date = models.DateField(null=True, blank=True)
    closed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_savings_accounts'
    )
    closure_reason = models.TextField(blank=True, null=True)

    # Additional features
    is_dormant = models.BooleanField(default=False)
    dormant_date = models.DateField(null=True, blank=True)
    last_transaction_date = models.DateField(null=True, blank=True)

    # Holds and restrictions
    total_holds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Linked loan information
    linked_loan_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="ID of loan this account is linked to"
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-opened_date']

    def __str__(self):
        return f"{self.account_number} - {self.borrower.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)

    def generate_account_number(self):
        """Generate a unique account number using sequential format: SV-0001."""
        last_account = SavingsAccount.objects.filter(
            account_number__startswith='SV-'
        ).order_by('account_number').last()
        
        if last_account:
            last_number = int(last_account.account_number[3:])  # Extract digits after 'SV-'
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"SV-{new_number:04d}"

    @property
    def minimum_balance_required(self):
        """Get minimum balance from product."""
        return self.savings_product.minimum_balance

    @property
    def current_interest_rate(self):
        """Get current interest rate from product."""
        return self.savings_product.interest_rate

    @property
    def is_below_minimum_balance(self):
        """Check if account is below minimum balance."""
        return self.balance < self.minimum_balance_required

    @property
    def days_since_last_transaction(self):
        """Calculate days since last transaction."""
        if self.last_transaction_date:
            return (timezone.now().date() - self.last_transaction_date).days
        return None

    @property
    def is_eligible_for_loan(self):
        """Check basic eligibility for loans based on account status."""
        return (
            self.status == SavingsAccountStatus.ACTIVE and
            not self.is_dormant and
            self.balance >= self.minimum_balance_required
        )

    def check_loan_eligibility(self, loan_category, loan_amount):
        """Check eligibility for specific loan category and amount."""
        if not self.is_eligible_for_loan:
            return False, "Account not eligible for loans"

        # Check savings rules for this loan category
        rules = SavingsLoanRule.objects.filter(
            loan_category=loan_category,
            is_active=True
        )

        for rule in rules:
            is_compliant, message = rule.check_compliance(self, loan_amount)
            if not is_compliant and rule.is_mandatory:
                return False, message

        return True, "All savings requirements met"

    def calculate_daily_interest(self):
        """Calculate daily interest based on current balance."""
        if self.balance <= 0:
            return Decimal('0.00')

        annual_rate = self.current_interest_rate / 100
        daily_rate = annual_rate / 365
        return self.balance * daily_rate

    def can_withdraw(self, amount):
        """Enhanced withdrawal validation."""
        if self.status != SavingsAccountStatus.ACTIVE:
            return False, "Account is not active"

        if amount <= 0:
            return False, "Invalid withdrawal amount"

        if amount > self.available_balance:
            return False, "Insufficient available balance"

        remaining_balance = self.balance - amount
        if remaining_balance < self.minimum_balance_required:
            return False, f"Withdrawal would bring balance below minimum required (Tsh {self.minimum_balance_required})"

        # Check daily withdrawal limit
        if self.savings_product.maximum_withdrawal_per_day:
            today_withdrawals = self.transactions.filter(
                transaction_type=TransactionTypeChoices.WITHDRAWAL,
                transaction_date=timezone.now().date()
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            if today_withdrawals + amount > self.savings_product.maximum_withdrawal_per_day:
                return False, f"Daily withdrawal limit of Tsh {self.savings_product.maximum_withdrawal_per_day} exceeded"

        return True, "Withdrawal allowed"

    def can_deposit(self, amount):
        """Check if deposit amount is allowed."""
        if self.status != SavingsAccountStatus.ACTIVE:
            return False, "Account is not active"

        if amount <= 0:
            return False, "Invalid deposit amount"

        if amount < self.savings_product.minimum_deposit:
            return False, f"Minimum deposit amount is Tsh {self.savings_product.minimum_deposit}"

        # Check maximum balance limit
        if self.savings_product.maximum_balance:
            if self.balance + amount > self.savings_product.maximum_balance:
                return False, f"Deposit would exceed maximum balance limit of Tsh {self.savings_product.maximum_balance}"

        # Check daily deposit limit
        if self.savings_product.maximum_deposit_per_day:
            today_deposits = self.transactions.filter(
                transaction_type=TransactionTypeChoices.DEPOSIT,
                transaction_date=timezone.now().date()
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            if today_deposits + amount > self.savings_product.maximum_deposit_per_day:
                return False, f"Daily deposit limit of Tsh {self.savings_product.maximum_deposit_per_day} exceeded"

        return True, "Deposit allowed"

    def deposit(self, amount, processed_by, notes=None):
        """Make a deposit to the account."""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        
        transaction = SavingsTransaction.objects.create(
            account=self,
            transaction_type='deposit',
            amount=amount,
            balance_before=self.balance,
            balance_after=self.balance + amount,
            processed_by=processed_by,
            notes=notes
        )
        
        self.balance += amount
        self.save()
        
        return transaction

    def withdraw(self, amount, processed_by, notes=None):
        """Make a withdrawal from the account."""
        can_withdraw, message = self.can_withdraw(amount)
        if not can_withdraw:
            raise ValueError(message)
        
        transaction = SavingsTransaction.objects.create(
            account=self,
            transaction_type='withdrawal',
            amount=amount,
            balance_before=self.balance,
            balance_after=self.balance - amount,
            processed_by=processed_by,
            notes=notes
        )
        
        self.balance -= amount
        self.save()
        
        return transaction


class SavingsTransaction(AuditModel):
    """
    Savings transaction model to track deposits and withdrawals.
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('interest', 'Interest'),
        ('fee', 'Fee'),
        ('charge', 'Charge'),
        ('transfer', 'Transfer'),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    savings_account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True
    )
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    # Charge information for fee/charge transactions
    related_charge = models.ForeignKey(
        SavingsCharge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    charge_description = models.CharField(max_length=200, blank=True, null=True)
    
    # Balance tracking
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Transaction details
    transaction_date = models.DateField(default=timezone.now)
    processed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='processed_savings_transactions'
    )
    reference_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )
    transaction_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True
    )
    
    status = models.CharField(
        max_length=15,
        choices=TRANSACTION_STATUS,
        default='pending'
    )
    
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.reference_number} - {self.transaction_type} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        if not self.transaction_id:
            self.transaction_id = self.reference_number  # Use same as reference for now
        super().save(*args, **kwargs)

    def generate_reference_number(self):
        """Generate a unique reference number using sequential format: TX-0001."""
        last_transaction = SavingsTransaction.objects.filter(
            reference_number__startswith='TX-'
        ).order_by('reference_number').last()
        
        if last_transaction:
            last_number = int(last_transaction.reference_number[3:])  # Extract digits after 'TX-'
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"TX-{new_number:04d}"


class SavingsInterestCalculation(models.Model):
    """Track interest calculations for savings accounts."""

    savings_account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name='interest_calculations'
    )
    calculation_date = models.DateField()
    period_start_date = models.DateField()
    period_end_date = models.DateField()

    # Balance information
    opening_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    closing_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    average_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Interest calculation
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    days_in_period = models.PositiveIntegerField()
    interest_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Status
    is_posted = models.BooleanField(default=False)
    posted_date = models.DateField(null=True, blank=True)
    posted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_interest_calculations'
    )

    # Journal entry reference for general ledger integration
    journal_entry_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Reference to journal entry in general ledger"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_interest_calculations'
    )

    class Meta:
        ordering = ['-calculation_date']
        unique_together = ['savings_account', 'period_start_date', 'period_end_date']

    def __str__(self):
        return f"{self.savings_account.account_number} - {self.calculation_date} - Tsh {self.interest_amount}"


class SavingsAccountHold(models.Model):
    """Track holds/freezes on savings account balances."""

    HOLD_TYPES = [
        ('loan_security', 'Loan Security'),
        ('legal_hold', 'Legal Hold'),
        ('administrative', 'Administrative Hold'),
        ('maintenance', 'Maintenance Hold'),
        ('other', 'Other'),
    ]

    HOLD_STATUS = [
        ('active', 'Active'),
        ('released', 'Released'),
        ('expired', 'Expired'),
    ]

    savings_account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name='holds'
    )
    hold_type = models.CharField(max_length=20, choices=HOLD_TYPES)
    hold_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Hold details
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    reason = models.TextField()
    hold_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=15, choices=HOLD_STATUS, default='active')
    released_date = models.DateField(null=True, blank=True)
    released_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_holds'
    )
    release_reason = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_holds'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.savings_account.account_number} - {self.get_hold_type_display()} - Tsh {self.hold_amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update total holds on savings account
        self.update_account_holds()

    def update_account_holds(self):
        """Update total holds on the savings account."""
        total_holds = self.savings_account.holds.filter(
            status='active'
        ).aggregate(total=Sum('hold_amount'))['total'] or Decimal('0.00')

        self.savings_account.total_holds = total_holds
        self.savings_account.save()

    def release_hold(self, released_by, reason=None):
        """Release this hold."""
        self.status = 'released'
        self.released_date = timezone.now().date()
        self.released_by = released_by
        if reason:
            self.release_reason = reason
        self.save()


