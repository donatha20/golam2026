"""
Employee Payroll models for the microfinance system.
Handles employee management, payroll processing, and related operations.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Sum, Q
from decimal import Decimal
from apps.core.models import AuditModel
from apps.accounts.models import CustomUser
import uuid


class Department(AuditModel):
    """Department model for organizing employees."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, null=True)
    head_of_department = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Position(AuditModel):
    """Job position/designation model."""
    title = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='positions'
    )
    description = models.TextField(blank=True, null=True)
    grade = models.CharField(max_length=10, blank=True, null=True)
    minimum_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    maximum_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['department', 'title']
        unique_together = ['title', 'department']
    
    def __str__(self):
        return f"{self.title} - {self.department.name}"


class Employee(AuditModel):
    """Employee model with comprehensive details."""
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('intern', 'Intern'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('resigned', 'Resigned'),
    ]
    
    # Personal Information
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique employee identification number"
    )
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile'
    )
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    
    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?[1-9]\d{1,14}$',
            message="Enter a valid phone number"
        )]
    )
    email = models.EmailField(unique=True)
    address = models.TextField()
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    
    # Employment Details
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Salary Information
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, default='TZS')
    
    # Bank Details
    bank_name = models.CharField(max_length=100)
    bank_account_number = models.CharField(max_length=50)
    bank_branch = models.CharField(max_length=100, blank=True, null=True)
    
    # Tax & Statutory Information
    tax_id_number = models.CharField(max_length=50, blank=True, null=True)
    nssf_number = models.CharField(max_length=50, blank=True, null=True)
    nhif_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Additional Information
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    notes = models.TextField(blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to='employee_photos/',
        blank=True,
        null=True
    )
    
    class Meta:
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['status']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.employee_id} - {self.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        super().save(*args, **kwargs)
    
    def generate_employee_id(self):
        """Generate unique employee ID."""
        import random
        import string
        
        # Format: EMP + Year + Department Code + 4 random digits
        current_year = timezone.now().year
        dept_code = self.department.code.upper()
        random_part = ''.join(random.choices(string.digits, k=4))
        employee_id = f"EMP{current_year}{dept_code}{random_part}"
        
        # Ensure uniqueness
        while Employee.objects.filter(employee_id=employee_id).exists():
            random_part = ''.join(random.choices(string.digits, k=4))
            employee_id = f"EMP{current_year}{dept_code}{random_part}"
        
        return employee_id
    
    def get_full_name(self):
        """Get employee's full name."""
        names = [self.first_name]
        if self.middle_name:
            names.append(self.middle_name)
        names.append(self.last_name)
        return ' '.join(names)
    
    @property
    def is_active(self):
        """Check if employee is active."""
        return self.status == 'active'
    
    @property
    def years_of_service(self):
        """Calculate years of service."""
        end_date = self.termination_date or timezone.now().date()
        service_period = end_date - self.hire_date
        return service_period.days / 365.25
    
    @property
    def current_age(self):
        """Calculate current age."""
        today = timezone.now().date()
        age = today - self.date_of_birth
        return int(age.days / 365.25)
    
    def deactivate(self, termination_date=None, reason=None):
        """Deactivate employee."""
        self.status = 'terminated'
        self.termination_date = termination_date or timezone.now().date()
        if reason:
            self.notes = f"{self.notes or ''}\nTermination: {reason}".strip()
        self.save()
    
    def reactivate(self):
        """Reactivate employee."""
        self.status = 'active'
        self.termination_date = None
        self.save()


class PayrollPeriod(AuditModel):
    """Payroll period model to define pay cycles."""
    
    PERIOD_TYPE_CHOICES = [
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=100)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    pay_date = models.DateField()
    
    # Status and processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_processed = models.BooleanField(default=False)
    processed_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payrolls'
    )
    
    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payrolls'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    
    # Totals
    total_employees = models.PositiveIntegerField(default=0)
    total_gross_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_deductions = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_net_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['period_type', 'start_date', 'end_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    @property
    def duration_days(self):
        """Calculate period duration in days."""
        return (self.end_date - self.start_date).days + 1
    
    def can_be_processed(self):
        """Check if payroll can be processed."""
        return self.status in ['draft'] and not self.is_processed
    
    def process_payroll(self, processed_by):
        """Process payroll for this period."""
        if not self.can_be_processed():
            raise ValueError("Payroll cannot be processed in current status")
        
        self.status = 'processing'
        self.save()
        
        # Get all active employees
        active_employees = Employee.objects.filter(
            status='active',
            hire_date__lte=self.end_date
        )
        
        total_employees = 0
        total_gross = Decimal('0.00')
        total_deductions = Decimal('0.00')
        total_net = Decimal('0.00')
        
        for employee in active_employees:
            # Create or update payroll record for employee
            payroll_record, created = PayrollRecord.objects.get_or_create(
                employee=employee,
                payroll_period=self,
                defaults={
                    'basic_salary': employee.basic_salary,
                    'status': 'draft'
                }
            )
            
            # Calculate payroll
            payroll_record.calculate_payroll()
            
            total_employees += 1
            total_gross += payroll_record.gross_salary
            total_deductions += payroll_record.total_deductions
            total_net += payroll_record.net_salary
        
        # Update period totals
        self.total_employees = total_employees
        self.total_gross_salary = total_gross
        self.total_deductions = total_deductions
        self.total_net_salary = total_net
        self.status = 'completed'
        self.is_processed = True
        self.processed_date = timezone.now()
        self.processed_by = processed_by
        
        self.save()
    
    def approve_payroll(self, approved_by):
        """Approve processed payroll."""
        if self.status != 'completed':
            raise ValueError("Only completed payrolls can be approved")
        
        self.status = 'approved'
        self.is_approved = True
        self.approved_by = approved_by
        self.approval_date = timezone.now()
        self.save()
        
        # Update all payroll records status
        self.payroll_records.update(status='approved')


class AllowanceType(AuditModel):
    """Types of allowances that can be given to employees."""
    
    CALCULATION_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Basic Salary'),
        ('variable', 'Variable Amount'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPE_CHOICES)
    default_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Default amount or percentage"
    )
    is_taxable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class DeductionType(AuditModel):
    """Types of deductions that can be applied to employees."""
    
    CALCULATION_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Gross Salary'),
        ('variable', 'Variable Amount'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPE_CHOICES)
    default_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Default amount or percentage"
    )
    is_statutory = models.BooleanField(default=False, help_text="Statutory deduction like PAYE, NSSF")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class EmployeeAllowance(AuditModel):
    """Employee-specific allowances."""
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='allowances'
    )
    allowance_type = models.ForeignKey(
        AllowanceType,
        on_delete=models.PROTECT,
        related_name='employee_allowances'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    effective_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['employee', 'allowance_type']
        unique_together = ['employee', 'allowance_type', 'effective_date']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.allowance_type.name}"
    
    @property
    def is_current(self):
        """Check if allowance is currently effective."""
        today = timezone.now().date()
        if not self.is_active:
            return False
        if self.effective_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True


class EmployeeDeduction(AuditModel):
    """Employee-specific deductions."""
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='deductions'
    )
    deduction_type = models.ForeignKey(
        DeductionType,
        on_delete=models.PROTECT,
        related_name='employee_deductions'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    effective_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['employee', 'deduction_type']
        unique_together = ['employee', 'deduction_type', 'effective_date']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.deduction_type.name}"
    
    @property
    def is_current(self):
        """Check if deduction is currently effective."""
        today = timezone.now().date()
        if not self.is_active:
            return False
        if self.effective_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True


class PayrollRecord(AuditModel):
    """Individual employee payroll record for a specific period."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='payroll_records'
    )
    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='payroll_records'
    )
    
    # Basic Salary
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Earnings
    total_allowances = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    overtime_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    bonus_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    gross_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Deductions
    paye_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    nssf_contribution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    nhif_contribution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_other_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    loan_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    advance_deduction_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Advance deduction amount"
    )
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Net Pay
    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Working days
    working_days = models.PositiveIntegerField(default=0)
    days_worked = models.PositiveIntegerField(default=0)
    days_absent = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    calculation_date = models.DateTimeField(null=True, blank=True)
    
    # Payment tracking
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-payroll_period__start_date', 'employee__employee_id']
        unique_together = ['employee', 'payroll_period']
        indexes = [
            models.Index(fields=['employee', 'payroll_period']),
            models.Index(fields=['status']),
            models.Index(fields=['is_paid']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.payroll_period.name}"
    
    def calculate_payroll(self):
        """Calculate payroll for this employee and period."""
        # Calculate working days
        self.calculate_working_days()
        
        # Calculate pro-rated basic salary if needed
        if self.days_worked < self.working_days:
            self.basic_salary = (self.employee.basic_salary / self.working_days) * self.days_worked
        else:
            self.basic_salary = self.employee.basic_salary
        
        # Calculate allowances
        self.calculate_allowances()
        
        # Calculate overtime and bonuses
        self.calculate_overtime_and_bonuses()
        
        # Calculate gross salary
        self.gross_salary = (
            self.basic_salary + self.total_allowances + 
            self.overtime_amount + self.bonus_amount
        )
        
        # Calculate deductions
        self.calculate_deductions()
        
        # Calculate net salary
        self.net_salary = self.gross_salary - self.total_deductions
        
        # Update status
        self.status = 'calculated'
        self.calculation_date = timezone.now()
        
        self.save()
    
    def calculate_working_days(self):
        """Calculate working days in the payroll period."""
        # Simple calculation - can be enhanced with holidays and weekends
        period_days = (self.payroll_period.end_date - self.payroll_period.start_date).days + 1
        
        # Assume 5 working days per week (can be customized)
        total_days = period_days
        weekends = period_days // 7 * 2  # Approximate weekends
        self.working_days = max(1, total_days - weekends)
        
        # Default to full attendance unless specified otherwise
        self.days_worked = self.working_days
        self.days_absent = 0
    
    def calculate_allowances(self):
        """Calculate total allowances for this employee."""
        allowances = self.employee.allowances.filter(
            is_active=True,
            effective_date__lte=self.payroll_period.end_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=self.payroll_period.start_date)
        )
        
        total_allowances = Decimal('0.00')
        
        for allowance in allowances:
            if allowance.allowance_type.calculation_type == 'fixed':
                amount = allowance.amount
            elif allowance.allowance_type.calculation_type == 'percentage':
                amount = (self.basic_salary * allowance.amount) / 100
            else:  # variable
                amount = allowance.amount
            
            total_allowances += amount
            
            # Create allowance record
            PayrollAllowance.objects.update_or_create(
                payroll_record=self,
                allowance_type=allowance.allowance_type,
                defaults={
                    'amount': amount,
                    'base_amount': allowance.amount
                }
            )
        
        self.total_allowances = total_allowances
    
    def calculate_overtime_and_bonuses(self):
        """Calculate overtime and bonuses."""
        # Get overtime records for this period
        overtime_records = OvertimeRecord.objects.filter(
            employee=self.employee,
            date__range=[self.payroll_period.start_date, self.payroll_period.end_date],
            is_approved=True
        )
        
        self.overtime_amount = sum(record.total_amount for record in overtime_records)
        
        # Get bonus records for this period
        bonus_records = BonusRecord.objects.filter(
            employee=self.employee,
            payroll_period=self.payroll_period,
            is_approved=True
        )
        
        self.bonus_amount = sum(record.amount for record in bonus_records)
    
    def calculate_deductions(self):
        """Calculate all deductions."""
        # PAYE Tax (simplified calculation)
        self.calculate_paye_tax()
        
        # NSSF Contribution (simplified)
        self.calculate_nssf()
        
        # NHIF Contribution (simplified)
        self.calculate_nhif()
        
        # Other deductions
        self.calculate_other_deductions()
        
        # Loan deductions
        self.calculate_loan_deductions()
        
        # Advance deductions
        self.calculate_advance_deductions()
        
        # Total deductions
        self.total_deductions = (
            self.paye_tax + self.nssf_contribution + self.nhif_contribution +
            self.total_other_deductions + self.loan_deductions + self.advance_deduction_amount
        )
    
    def calculate_paye_tax(self):
        """Calculate PAYE tax (simplified Tanzania tax calculation)."""
        # This is a simplified calculation - should be based on actual tax bands
        taxable_income = self.gross_salary
        
        if taxable_income <= 170000:  # Tax-free threshold
            self.paye_tax = Decimal('0.00')
        elif taxable_income <= 360000:
            self.paye_tax = (taxable_income - 170000) * Decimal('0.09')  # 9%
        elif taxable_income <= 540000:
            self.paye_tax = 17100 + (taxable_income - 360000) * Decimal('0.20')  # 20%
        elif taxable_income <= 720000:
            self.paye_tax = 53100 + (taxable_income - 540000) * Decimal('0.25')  # 25%
        else:
            self.paye_tax = 98100 + (taxable_income - 720000) * Decimal('0.30')  # 30%
    
    def calculate_nssf(self):
        """Calculate NSSF contribution."""
        # NSSF contribution is typically 10% of basic salary (5% employee + 5% employer)
        # Here we calculate only employee portion (5%)
        self.nssf_contribution = min(
            self.basic_salary * Decimal('0.05'),
            Decimal('20000')  # Maximum NSSF contribution
        )
    
    def calculate_nhif(self):
        """Calculate NHIF contribution."""
        # Simplified NHIF calculation based on gross salary
        gross = self.gross_salary
        
        if gross <= 15000:
            self.nhif_contribution = Decimal('0')
        elif gross <= 20000:
            self.nhif_contribution = Decimal('300')
        elif gross <= 25000:
            self.nhif_contribution = Decimal('400')
        elif gross <= 30000:
            self.nhif_contribution = Decimal('500')
        elif gross <= 35000:
            self.nhif_contribution = Decimal('600')
        elif gross <= 40000:
            self.nhif_contribution = Decimal('750')
        elif gross <= 45000:
            self.nhif_contribution = Decimal('900')
        elif gross <= 50000:
            self.nhif_contribution = Decimal('1000')
        elif gross <= 60000:
            self.nhif_contribution = Decimal('1200')
        elif gross <= 70000:
            self.nhif_contribution = Decimal('1500')
        elif gross <= 80000:
            self.nhif_contribution = Decimal('1800')
        elif gross <= 90000:
            self.nhif_contribution = Decimal('2100')
        elif gross <= 100000:
            self.nhif_contribution = Decimal('2400')
        else:
            self.nhif_contribution = Decimal('2700')
    
    def calculate_other_deductions(self):
        """Calculate other deductions."""
        deductions = self.employee.deductions.filter(
            is_active=True,
            effective_date__lte=self.payroll_period.end_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=self.payroll_period.start_date)
        )
        
        total_deductions = Decimal('0.00')
        
        for deduction in deductions:
            if deduction.deduction_type.calculation_type == 'fixed':
                amount = deduction.amount
            elif deduction.deduction_type.calculation_type == 'percentage':
                amount = (self.gross_salary * deduction.amount) / 100
            else:  # variable
                amount = deduction.amount
            
            total_deductions += amount
            
            # Create deduction record
            PayrollDeduction.objects.update_or_create(
                payroll_record=self,
                deduction_type=deduction.deduction_type,
                defaults={
                    'amount': amount,
                    'base_amount': deduction.amount
                }
            )
        
        self.total_other_deductions = total_deductions
    
    def calculate_loan_deductions(self):
        """Calculate loan deductions from employee loans."""
        # This would integrate with the loans app
        self.loan_deductions = Decimal('0.00')  # Placeholder
    
    def calculate_advance_deductions(self):
        """Calculate salary advance deductions."""
        advances = SalaryAdvance.objects.filter(
            employee=self.employee,
            status='approved',
            repayment_start_date__lte=self.payroll_period.end_date
        )
        
        total_advance_deductions = Decimal('0.00')
        
        for advance in advances:
            if advance.remaining_balance > 0:
                deduction_amount = min(advance.monthly_deduction, advance.remaining_balance)
                total_advance_deductions += deduction_amount
                
                # Update advance balance
                advance.remaining_balance -= deduction_amount
                if advance.remaining_balance <= 0:
                    advance.status = 'fully_repaid'
                advance.save()
                
                # Create advance deduction record
                AdvanceDeduction.objects.create(
                    payroll_record=self,
                    salary_advance=advance,
                    amount=deduction_amount
                )
        
        self.advance_deduction_amount = total_advance_deductions
    
    def generate_payslip(self):
        """Generate payslip for this payroll record."""
        if self.status not in ['calculated', 'approved', 'paid']:
            raise ValueError("Payslip can only be generated for calculated payroll")
        
        payslip, created = Payslip.objects.get_or_create(
            payroll_record=self,
            defaults={
                'generated_date': timezone.now(),
                'payslip_number': self.generate_payslip_number()
            }
        )
        
        return payslip
    
    def generate_payslip_number(self):
        """Generate unique payslip number."""
        import random
        import string
        
        # Format: PS + Year + Month + Employee ID + 3 random digits
        period_start = self.payroll_period.start_date
        year_month = f"{period_start.year}{period_start.month:02d}"
        emp_id = self.employee.employee_id[-4:]  # Last 4 digits of employee ID
        random_part = ''.join(random.choices(string.digits, k=3))
        
        return f"PS{year_month}{emp_id}{random_part}"


class PayrollAllowance(models.Model):
    """Track individual allowances in payroll records."""
    
    payroll_record = models.ForeignKey(
        PayrollRecord,
        on_delete=models.CASCADE,
        related_name='payroll_allowances'
    )
    allowance_type = models.ForeignKey(
        AllowanceType,
        on_delete=models.PROTECT
    )
    base_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Base amount or percentage used for calculation"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Calculated allowance amount"
    )
    
    class Meta:
        unique_together = ['payroll_record', 'allowance_type']
    
    def __str__(self):
        return f"{self.payroll_record} - {self.allowance_type.name}"


class PayrollDeduction(models.Model):
    """Track individual deductions in payroll records."""
    
    payroll_record = models.ForeignKey(
        PayrollRecord,
        on_delete=models.CASCADE,
        related_name='payroll_deductions'
    )
    deduction_type = models.ForeignKey(
        DeductionType,
        on_delete=models.PROTECT
    )
    base_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Base amount or percentage used for calculation"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Calculated deduction amount"
    )
    
    class Meta:
        unique_together = ['payroll_record', 'deduction_type']
    
    def __str__(self):
        return f"{self.payroll_record} - {self.deduction_type.name}"


class OvertimeRecord(AuditModel):
    """Track employee overtime hours and payments."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='overtime_records'
    )
    date = models.DateField()
    regular_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('8.00'),
        help_text="Regular working hours for the day"
    )
    overtime_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    overtime_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.50'),
        help_text="Overtime rate multiplier (e.g., 1.5 for time and half)"
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Hourly rate for overtime calculation"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Approval
    submitted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_overtime'
    )
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_overtime'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['employee', 'date']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date} ({self.overtime_hours}h)"
    
    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = self.overtime_hours * self.hourly_rate * self.overtime_rate
        super().save(*args, **kwargs)
    
    @property
    def is_approved(self):
        return self.status == 'approved'


class BonusRecord(AuditModel):
    """Track employee bonuses."""
    
    BONUS_TYPE_CHOICES = [
        ('performance', 'Performance Bonus'),
        ('annual', 'Annual Bonus'),
        ('project', 'Project Bonus'),
        ('retention', 'Retention Bonus'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='bonus_records'
    )
    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='bonus_records'
    )
    bonus_type = models.CharField(max_length=20, choices=BONUS_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    description = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_bonuses'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.get_bonus_type_display()} - Tsh {self.amount}"


class SalaryAdvance(AuditModel):
    """Track salary advances given to employees."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('partially_repaid', 'Partially Repaid'),
        ('fully_repaid', 'Fully Repaid'),
        ('written_off', 'Written Off'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='salary_advances'
    )
    advance_number = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reason = models.TextField()
    
    # Repayment terms
    monthly_deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    number_of_installments = models.PositiveIntegerField()
    repayment_start_date = models.DateField()
    
    # Tracking
    remaining_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_repaid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval
    requested_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_advances'
    )
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_advances'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    
    # Disbursement
    disbursement_date = models.DateField(null=True, blank=True)
    disbursed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disbursed_advances'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.advance_number} - {self.employee.get_full_name()} - Tsh {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.advance_number:
            self.advance_number = self.generate_advance_number()
        
        if self.status == 'approved' and not self.remaining_balance:
            self.remaining_balance = self.amount
        
        super().save(*args, **kwargs)
    
    def generate_advance_number(self):
        """Generate unique advance number."""
        import random
        import string
        
        # Format: ADV + Year + Month + 6 random digits
        now = timezone.now()
        year_month = f"{now.year}{now.month:02d}"
        random_part = ''.join(random.choices(string.digits, k=6))
        advance_number = f"ADV{year_month}{random_part}"
        
        # Ensure uniqueness
        while SalaryAdvance.objects.filter(advance_number=advance_number).exists():
            random_part = ''.join(random.choices(string.digits, k=6))
            advance_number = f"ADV{year_month}{random_part}"
        
        return advance_number


class AdvanceDeduction(models.Model):
    """Track advance deductions from payroll."""
    
    payroll_record = models.ForeignKey(
        PayrollRecord,
        on_delete=models.CASCADE,
        related_name='advance_deductions'
    )
    salary_advance = models.ForeignKey(
        SalaryAdvance,
        on_delete=models.CASCADE,
        related_name='deductions'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    deduction_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-deduction_date']
    
    def __str__(self):
        return f"{self.salary_advance.advance_number} - Tsh {self.amount}"


class Payslip(models.Model):
    """Generated payslip for employees."""
    
    payroll_record = models.OneToOneField(
        PayrollRecord,
        on_delete=models.CASCADE,
        related_name='payslip'
    )
    payslip_number = models.CharField(max_length=20, unique=True)
    generated_date = models.DateTimeField()
    generated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_payslips'
    )
    
    # Access tracking
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-generated_date']
    
    def __str__(self):
        return f"Payslip {self.payslip_number} - {self.payroll_record.employee.get_full_name()}"
    
    def record_download(self):
        """Record payslip download."""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save()


class PayrollReport(AuditModel):
    """Generate and store payroll reports."""
    
    REPORT_TYPE_CHOICES = [
        ('payroll_summary', 'Payroll Summary'),
        ('tax_report', 'Tax Report'),
        ('statutory_report', 'Statutory Deductions Report'),
        ('department_summary', 'Department Summary'),
        ('employee_summary', 'Employee Summary'),
    ]
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    report_name = models.CharField(max_length=200)
    
    # Filters
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Report data
    report_data = models.JSONField(default=dict)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    
    generated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_payroll_reports'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_name} - {self.payroll_period}"
