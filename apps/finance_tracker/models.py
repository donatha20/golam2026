from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class IncomeCategory(models.Model):
    """Categories for income classification"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Income Categories"

    def __str__(self):
        return self.name


class ExpenditureCategory(models.Model):
    """Categories for expenditure classification"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Expenditure Categories"

    def __str__(self):
        return self.name


class Income(models.Model):
    """Model for tracking income"""
    INCOME_SOURCES = [
        ('loan_interest', 'Loan Interest'),
        ('service_fees', 'Service Fees'),
        ('membership_fees', 'Membership Fees'),
        ('investment_returns', 'Investment Returns'),
        ('donations', 'Donations'),
        ('other', 'Other Income'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Core fields
    income_id = models.CharField(max_length=20, unique=True, blank=True)
    source = models.CharField(max_length=20, choices=INCOME_SOURCES)
    category = models.ForeignKey(IncomeCategory, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField()
    date = models.DateField(default=timezone.now)
    income_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Additional details
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    received_from = models.CharField(max_length=200, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)

    # Approval fields
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_income')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_income')

    class Meta:
        ordering = ['-income_date', '-created_at']

    def __str__(self):
        return f"{self.get_source_display()} - TSh {self.amount:,.2f}"

    def get_source_display(self):
        """Return source label from Settings (core.IncomeSource) with fallback to static choices."""
        from apps.core.models import IncomeSource

        source = IncomeSource.objects.filter(code=self.source).first()
        if source:
            return source.name

        return dict(self.INCOME_SOURCES).get(self.source, self.source)

    def save(self, *args, **kwargs):
        if not self.income_id:
            # Generate income ID
            last_income = Income.objects.filter(
                income_id__startswith='INC'
            ).order_by('income_id').last()

            if last_income:
                last_number = int(last_income.income_id[3:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.income_id = f"INC{new_number:06d}"

        super().save(*args, **kwargs)


class Expenditure(models.Model):
    """Model for tracking expenditures"""
    EXPENDITURE_TYPES = [
        ('operational', 'Operational Expenses'),
        ('administrative', 'Administrative Expenses'),
        ('staff_costs', 'Staff Costs'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent & Facilities'),
        ('marketing', 'Marketing & Promotion'),
        ('equipment', 'Equipment & Supplies'),
        ('maintenance', 'Maintenance & Repairs'),
        ('professional_services', 'Professional Services'),
        ('travel', 'Travel & Transportation'),
        ('training', 'Training & Development'),
        ('other', 'Other Expenses'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
    ]

    expenditure_id = models.CharField(max_length=20, unique=True, blank=True)
    expenditure_type = models.CharField(max_length=25, choices=EXPENDITURE_TYPES)
    category = models.ForeignKey(ExpenditureCategory, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField()
    expenditure_date = models.DateField()

    # Vendor/Payee information
    vendor_name = models.CharField(max_length=200)
    vendor_contact = models.CharField(max_length=100, blank=True, null=True)

    # Payment details
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)

    # Approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenditures')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_expenditures')

    class Meta:
        ordering = ['-expenditure_date', '-created_at']

    def __str__(self):
        return f"{self.get_expenditure_type_display()} - TSh {self.amount:,.2f}"

    def get_expenditure_type_display(self):
        """Return expenditure type label from Settings (core.ExpenseCategory) with fallback to static choices."""
        from apps.core.models import ExpenseCategory

        category = ExpenseCategory.objects.filter(code=self.expenditure_type).first()
        if category:
            return category.name

        return dict(self.EXPENDITURE_TYPES).get(self.expenditure_type, self.expenditure_type)

    def save(self, *args, **kwargs):
        if not self.expenditure_id:
            # Generate expenditure ID
            last_expenditure = Expenditure.objects.filter(
                expenditure_id__startswith='EXP'
            ).order_by('expenditure_id').last()

            if last_expenditure:
                last_number = int(last_expenditure.expenditure_id[3:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.expenditure_id = f"EXP{new_number:06d}"

        super().save(*args, **kwargs)


class Budget(models.Model):
    """Model for budget planning and tracking."""

    BUDGET_STATUS = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    BUDGET_PERIOD = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ]

    budget_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    # Period details
    budget_period = models.CharField(max_length=20, choices=BUDGET_PERIOD)
    period_start = models.DateField()
    period_end = models.DateField()

    # Budget amounts
    total_income_budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_expenditure_budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    net_budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Status and approval
    status = models.CharField(max_length=20, choices=BUDGET_STATUS, default='draft')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_budgets'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_budgets'
    )

    class Meta:
        ordering = ['-period_start']
        unique_together = ['budget_period', 'period_start', 'period_end']

    def __str__(self):
        return f"{self.name} - {self.period_start} to {self.period_end}"

    def save(self, *args, **kwargs):
        # Generate budget ID
        if not self.budget_id:
            last_budget = Budget.objects.filter(
                budget_id__startswith='BUD'
            ).order_by('budget_id').last()

            if last_budget:
                last_number = int(last_budget.budget_id[3:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.budget_id = f"BUD{new_number:06d}"

        # Calculate net budget
        self.net_budget = self.total_income_budget - self.total_expenditure_budget

        super().save(*args, **kwargs)

    @property
    def actual_income(self):
        """Calculate actual income for the budget period."""
        return Income.objects.filter(
            income_date__range=[self.period_start, self.period_end]
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def actual_expenditure(self):
        """Calculate actual expenditure for the budget period."""
        return Expenditure.objects.filter(
            expenditure_date__range=[self.period_start, self.period_end],
            status='paid'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def income_variance(self):
        """Calculate income variance (actual vs budget)."""
        return self.actual_income - self.total_income_budget

    @property
    def expenditure_variance(self):
        """Calculate expenditure variance (actual vs budget)."""
        return self.actual_expenditure - self.total_expenditure_budget

    @property
    def income_variance_percentage(self):
        """Calculate income variance percentage."""
        if self.total_income_budget > 0:
            return (self.income_variance / self.total_income_budget) * 100
        return Decimal('0.00')

    @property
    def expenditure_variance_percentage(self):
        """Calculate expenditure variance percentage."""
        if self.total_expenditure_budget > 0:
            return (self.expenditure_variance / self.total_expenditure_budget) * 100
        return Decimal('0.00')


class Shareholder(models.Model):
    """Model for managing shareholders"""
    SHAREHOLDER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('institutional', 'Institutional'),
        ('founder', 'Founder'),
        ('employee', 'Employee'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    # Basic Information
    shareholder_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    shareholder_type = models.CharField(max_length=20, choices=SHAREHOLDER_TYPE_CHOICES)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Share Information
    shares_owned = models.PositiveIntegerField(default=0)
    share_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_investment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    join_date = models.DateField(default=timezone.now)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_shareholders')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.shares_owned} shares)"

    def save(self, *args, **kwargs):
        if not self.shareholder_id:
            # Generate shareholder ID
            last_shareholder = Shareholder.objects.filter(
                shareholder_id__startswith='SH'
            ).order_by('shareholder_id').last()

            if last_shareholder:
                last_number = int(last_shareholder.shareholder_id[2:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.shareholder_id = f"SH{new_number:06d}"

        # Calculate total investment
        self.total_investment = self.shares_owned * self.share_value

        super().save(*args, **kwargs)


class Capital(models.Model):
    """Model for managing capital transactions"""
    CAPITAL_TYPE_CHOICES = [
        ('share_capital', 'Share Capital'),
        ('retained_earnings', 'Retained Earnings'),
        ('additional_capital', 'Additional Capital'),
        ('capital_reserve', 'Capital Reserve'),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ('injection', 'Capital Injection'),
        ('withdrawal', 'Capital Withdrawal'),
        ('transfer', 'Capital Transfer'),
        ('adjustment', 'Capital Adjustment'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Core fields
    capital_id = models.CharField(max_length=20, unique=True, blank=True)
    capital_type = models.CharField(max_length=20, choices=CAPITAL_TYPE_CHOICES)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.TextField()
    transaction_date = models.DateField(default=timezone.now)

    # Related information
    shareholder = models.ForeignKey(
        Shareholder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='capital_transactions'
    )
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_capital'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_capital')

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.get_capital_type_display()} - TSh {self.amount:,.2f}"

    def save(self, *args, **kwargs):
        if not self.capital_id:
            # Generate capital ID
            last_capital = Capital.objects.filter(
                capital_id__startswith='CAP'
            ).order_by('capital_id').last()

            if last_capital:
                last_number = int(last_capital.capital_id[3:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.capital_id = f"CAP{new_number:06d}"

        super().save(*args, **kwargs)


class BudgetLineItem(models.Model):
    """Detailed budget line items for income and expenditure categories."""

    ITEM_TYPE = [
        ('income', 'Income'),
        ('expenditure', 'Expenditure'),
    ]

    budget = models.ForeignKey(
        'Budget',
        on_delete=models.CASCADE,
        related_name='line_items'
    )

    # Item details
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE)
    income_category = models.ForeignKey(
        'IncomeCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_items'
    )
    expenditure_category = models.ForeignKey(
        'ExpenditureCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_items'
    )

    # Budget amounts
    budgeted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Description and notes
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['item_type', 'income_category', 'expenditure_category']
        unique_together = [
            ['budget', 'income_category'],
            ['budget', 'expenditure_category']
        ]

    def __str__(self):
        if self.item_type == 'income':
            category_name = self.income_category.name if self.income_category else 'Uncategorized'
        else:
            category_name = self.expenditure_category.name if self.expenditure_category else 'Uncategorized'

        return f"{self.budget.name} - {category_name} - TSh {self.budgeted_amount:,.2f}"

    @property
    def actual_amount(self):
        """Calculate actual amount for this budget line item."""
        if self.item_type == 'income':
            if self.income_category:
                return Income.objects.filter(
                    category=self.income_category,
                    income_date__range=[self.budget.period_start, self.budget.period_end]
                ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        else:
            if self.expenditure_category:
                return Expenditure.objects.filter(
                    category=self.expenditure_category,
                    expenditure_date__range=[self.budget.period_start, self.budget.period_end],
                    status='paid'
                ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        return Decimal('0.00')

    @property
    def variance(self):
        """Calculate variance (actual vs budgeted)."""
        return self.actual_amount - self.budgeted_amount

    @property
    def variance_percentage(self):
        """Calculate variance percentage."""
        if self.budgeted_amount > 0:
            return (self.variance / self.budgeted_amount) * 100
        return Decimal('0.00')


class ExpenseApprovalWorkflow(models.Model):
    """Track expense approval workflow."""

    APPROVAL_LEVEL = [
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('board', 'Board of Directors'),
    ]

    WORKFLOW_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated'),
    ]

    expenditure = models.ForeignKey(
        'Expenditure',
        on_delete=models.CASCADE,
        related_name='approval_workflow'
    )

    # Approval details
    approval_level = models.CharField(max_length=20, choices=APPROVAL_LEVEL)
    required_amount_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Approver information
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expense_approvals'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    # Status and comments
    status = models.CharField(max_length=20, choices=WORKFLOW_STATUS, default='pending')
    comments = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Escalation
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_expenses'
    )
    escalation_date = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['approval_level', 'created_at']
        unique_together = ['expenditure', 'approval_level']

    def __str__(self):
        return f"{self.expenditure.expenditure_id} - {self.get_approval_level_display()} - {self.status}"


