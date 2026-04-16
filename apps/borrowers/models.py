"""
Borrower management models for the microfinance system.
"""
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from apps.core.models import (
    AuditModel, GenderChoices, MaritalStatusChoices, 
    IDTypeChoices, StatusChoices, Branch
)
from apps.accounts.models import CustomUser
import uuid


class BorrowerStatus(models.TextChoices):
    """Borrower status choices."""
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    BLACKLISTED = 'blacklisted', 'Blacklisted'
    INACTIVE = 'inactive', 'Inactive'


class Borrower(AuditModel):
    """
    Borrower model containing all borrower information.
    """
    # System generated fields
    borrower_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="Auto-generated unique borrower reference number"
    )
    
    # Personal Details
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GenderChoices.choices)
    date_of_birth = models.DateField()
    marital_status = models.CharField(max_length=15, choices=MaritalStatusChoices.choices)
    occupation = models.CharField(max_length=100)
    
    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    email = models.EmailField(blank=True, null=True)
    photo = models.ImageField(upload_to='borrower_photos/', blank=True, null=True)
    
    # Identification Details
    id_type = models.CharField(max_length=20, choices=IDTypeChoices.choices)
    id_number = models.CharField(max_length=50, unique=True)
    id_issue_date = models.DateField(blank=True, null=True)
    id_expiry_date = models.DateField(blank=True, null=True)
    
    # Residential Address
    house_number = models.CharField(max_length=20, blank=True, null=True)
    street = models.CharField(max_length=100)
    ward = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    region = models.CharField(max_length=50)
    
    # Next of Kin Information
    next_of_kin_name = models.CharField(max_length=100)
    next_of_kin_relationship = models.CharField(max_length=50)
    next_of_kin_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    next_of_kin_address = models.TextField()
    
    # Registration Information
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='borrowers'
    )
    registered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='registered_borrowers'
    )
    registration_date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=15,
        choices=BorrowerStatus.choices,
        default=BorrowerStatus.ACTIVE
    )
    
    # Additional fields for system tracking
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-registration_date', 'first_name', 'last_name']
        indexes = [
            models.Index(fields=['borrower_id']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['id_number']),
            models.Index(fields=['status']),
            models.Index(fields=['registration_date']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.borrower_id})"

    def save(self, *args, **kwargs):
        if not self.borrower_id:
            self.borrower_id = self.generate_borrower_id()
        super().save(*args, **kwargs)

    def generate_borrower_id(self):
        """Generate a unique borrower ID using sequential format: BR-0001."""
        last_borrower = Borrower.objects.filter(
            borrower_id__startswith='BR-'
        ).order_by('borrower_id').last()
        
        if last_borrower:
            last_number = int(last_borrower.borrower_id[3:])  # Extract digits after 'BR-'
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"BR-{new_number:04d}"

    def get_full_name(self):
        """Return the full name of the borrower."""
        names = [self.first_name]
        if self.middle_name:
            names.append(self.middle_name)
        names.append(self.last_name)
        return ' '.join(names)

    def get_full_address(self):
        """Return the full address of the borrower."""
        address_parts = []
        if self.house_number:
            address_parts.append(self.house_number)
        address_parts.extend([self.street, self.ward, self.district, self.region])
        return ', '.join(filter(None, address_parts))

    @property
    def age(self):
        """Calculate and return the borrower's age."""
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def total_loans_taken(self):
        """Return the total number of loans taken by this borrower."""
        return self.loans.count()

    @property
    def total_amount_borrowed(self):
        """Return the total amount borrowed by this borrower."""
        from django.db.models import Sum
        return self.loans.aggregate(
            total=Sum('amount_approved')
        )['total'] or 0

    @property
    def total_amount_repaid(self):
        """Return the total amount repaid by this borrower."""
        from django.db.models import Sum
        return self.payments.aggregate(
            total=Sum('amount')
        )['total'] or 0

    @property
    def current_loan_status(self):
        """Return the current loan status of the borrower."""
        active_loan = self.loans.filter(
            status__in=['disbursed', 'active']
        ).first()
        
        if active_loan:
            return f"Active Loan: {active_loan.loan_number}"
        
        defaulted_loan = self.loans.filter(status='defaulted').first()
        if defaulted_loan:
            return "Defaulted"
        
        return "No Active Loan"

    def can_take_loan(self):
        """Check if borrower is eligible for a new loan."""
        if self.status != BorrowerStatus.ACTIVE:
            return False, "Borrower is not active"
        
        # Check for active loans
        active_loans = self.loans.filter(
            status__in=['disbursed', 'active']
        ).count()
        
        if active_loans > 0:
            return False, "Borrower has active loans"
        
        # Check for defaulted loans
        defaulted_loans = self.loans.filter(status='defaulted').count()
        if defaulted_loans > 0:
            return False, "Borrower has defaulted loans"
        
        return True, "Eligible for loan"


class BorrowerDocument(AuditModel):
    """
    Model to store borrower documents.
    """
    borrower = models.ForeignKey(
        Borrower,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=50)
    document_name = models.CharField(max_length=100)
    document_file = models.FileField(upload_to='borrower_documents/')
    description = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verification_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.borrower.get_full_name()} - {self.document_name}"


class BorrowerGroup(AuditModel):
    """
    Model for borrower groups for group loans.
    """
    group_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated unique group reference number"
    )
    group_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Group leadership
    group_leader = models.ForeignKey(
        Borrower,
        on_delete=models.PROTECT,
        related_name='led_groups'
    )

    # Group details
    formation_date = models.DateField(default=timezone.now)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='borrower_groups'
    )
    registered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='registered_groups'
    )

    # Group status
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    # Group settings
    minimum_members = models.PositiveIntegerField(default=5)
    maximum_members = models.PositiveIntegerField(default=20)
    meeting_frequency = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Weekly'),
            ('biweekly', 'Bi-weekly'),
            ('monthly', 'Monthly'),
        ],
        default='weekly'
    )
    meeting_day = models.CharField(
        max_length=10,
        choices=[
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ],
        blank=True,
        null=True
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-formation_date', 'group_name']
        indexes = [
            models.Index(fields=['group_id']),
            models.Index(fields=['group_name']),
            models.Index(fields=['status']),
            models.Index(fields=['formation_date']),
        ]

    def __str__(self):
        return f"{self.group_name} ({self.group_id})"

    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group_id = self.generate_group_id()
        super().save(*args, **kwargs)

    def generate_group_id(self):
        """Generate a unique group ID using sequential format: GR-0001."""
        last_group = BorrowerGroup.objects.filter(
            group_id__startswith='GR-'
        ).order_by('group_id').last()
        
        if last_group:
            last_number = int(last_group.group_id[3:])  # Extract digits after 'GR-'
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"GR-{new_number:04d}"

    @property
    def member_count(self):
        """Return the number of members in the group."""
        return self.members.count()

    @property
    def is_full(self):
        """Check if the group has reached maximum capacity."""
        return self.member_count >= self.maximum_members

    @property
    def can_take_loan(self):
        """Check if group meets minimum requirements for a loan."""
        return (
            self.status == StatusChoices.ACTIVE and
            self.member_count >= self.minimum_members
        )

    @property
    def total_group_loans(self):
        """Return the total number of group loans."""
        return self.group_loans.count()

    @property
    def active_group_loans(self):
        """Return the number of active group loans."""
        return self.group_loans.filter(
            status__in=['disbursed', 'active']
        ).count()


class GroupMembership(AuditModel):
    """
    Model for tracking group memberships.
    """
    group = models.ForeignKey(
        BorrowerGroup,
        on_delete=models.CASCADE,
        related_name='members'
    )
    borrower = models.ForeignKey(
        Borrower,
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )

    # Membership details
    join_date = models.DateField(default=timezone.now)
    leave_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Member role in group
    role = models.CharField(
        max_length=20,
        choices=[
            ('member', 'Member'),
            ('secretary', 'Secretary'),
            ('treasurer', 'Treasurer'),
            ('leader', 'Leader'),
        ],
        default='member'
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['group', 'borrower']
        ordering = ['-join_date']
        indexes = [
            models.Index(fields=['group', 'is_active']),
            models.Index(fields=['borrower', 'is_active']),
        ]

    def __str__(self):
        return f"{self.borrower.get_full_name()} - {self.group.group_name}"

    def leave_group(self):
        """Mark member as having left the group."""
        self.is_active = False
        self.leave_date = timezone.now().date()
        self.save()


