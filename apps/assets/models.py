"""
Asset and collateral management models for the microfinance system.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import os
from apps.core.models import AuditModel, StatusChoices
from apps.accounts.models import CustomUser

User = CustomUser
from apps.borrowers.models import Borrower
from apps.loans.models import Loan


class AssetCategory(models.Model):
    """Asset category for classification."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Annual depreciation rate as percentage"
    )
    useful_life_years = models.PositiveIntegerField(
        default=5,
        help_text="Expected useful life in years"
    )
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return self.name


class Asset(AuditModel):
    """Enhanced internal asset tracking model."""

    ASSET_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('under_maintenance', 'Under Maintenance'),
        ('disposed', 'Disposed'),
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
        ('stolen', 'Stolen'),
    ]

    CONDITION_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ]

    # Basic Information
    asset_id = models.CharField(max_length=20, unique=True, blank=True)
    asset_name = models.CharField(max_length=200)
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name='assets',
        null=True,
        blank=True
    )
    description = models.TextField(blank=True, null=True)

    # Financial Information
    purchase_date = models.DateField()
    purchase_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    salvage_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Depreciation
    depreciation_method = models.CharField(
        max_length=20,
        choices=[
            ('straight_line', 'Straight Line'),
            ('declining_balance', 'Declining Balance'),
            ('units_of_production', 'Units of Production'),
        ],
        default='straight_line'
    )
    custom_depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Override category depreciation rate if needed"
    )

    # Physical Information
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='good'
    )

    # Location and Assignment
    location = models.CharField(max_length=200, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets'
    )

    # Status and Maintenance
    status = models.CharField(
        max_length=20,
        choices=ASSET_STATUS_CHOICES,
        default='active'
    )
    warranty_expiry = models.DateField(null=True, blank=True)
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)

    # Additional Information
    supplier = models.CharField(max_length=200, blank=True, null=True)
    purchase_order_number = models.CharField(max_length=50, blank=True, null=True)
    insurance_policy_number = models.CharField(max_length=50, blank=True, null=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    # Disposal Information
    disposal_date = models.DateField(null=True, blank=True)
    disposal_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    disposal_method = models.CharField(max_length=100, blank=True, null=True)
    disposal_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['asset_name']

    def __str__(self):
        return f"{self.asset_id} - {self.asset_name}"

    def save(self, *args, **kwargs):
        if not self.asset_id:
            self.asset_id = self.generate_asset_id()
        super().save(*args, **kwargs)

    def generate_asset_id(self):
        """Generate unique asset ID."""
        last_asset = Asset.objects.filter(
            asset_id__startswith='AST'
        ).order_by('asset_id').last()

        if last_asset:
            last_number = int(last_asset.asset_id[3:])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"AST{new_number:06d}"

    @property
    def age_in_years(self):
        """Calculate asset age in years."""
        today = timezone.now().date()
        age = today - self.purchase_date
        return round(age.days / 365.25, 1)

    @property
    def depreciation_rate(self):
        """Get effective depreciation rate."""
        if self.custom_depreciation_rate:
            return self.custom_depreciation_rate
        return self.category.depreciation_rate

    @property
    def accumulated_depreciation(self):
        """Calculate accumulated depreciation."""
        if self.depreciation_method == 'straight_line':
            annual_depreciation = (self.purchase_value - self.salvage_value) * (self.depreciation_rate / 100)
            return min(annual_depreciation * self.age_in_years, self.purchase_value - self.salvage_value)
        return Decimal('0.00')

    @property
    def book_value(self):
        """Calculate current book value."""
        return max(self.purchase_value - self.accumulated_depreciation, self.salvage_value)

    @property
    def is_under_warranty(self):
        """Check if asset is still under warranty."""
        if self.warranty_expiry:
            return timezone.now().date() <= self.warranty_expiry
        return False

    @property
    def maintenance_due(self):
        """Check if maintenance is due."""
        if self.next_maintenance_date:
            return timezone.now().date() >= self.next_maintenance_date
        return False


class CollateralType(models.Model):
    """Collateral type classification."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    required_documents = models.TextField(
        blank=True,
        null=True,
        help_text="List of required documents for this collateral type"
    )
    minimum_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    loan_to_value_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('80.00'),
        validators=[MinValueValidator(Decimal('1.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Maximum loan-to-value ratio as percentage"
    )
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Collateral(AuditModel):
    """Enhanced collateral model for loan security."""

    COLLATERAL_STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_verification', 'Under Verification'),
        ('verified', 'Verified'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('held', 'Held as Security'),
        ('released', 'Released'),
        ('liquidated', 'Liquidated'),
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
    ]

    OWNERSHIP_STATUS_CHOICES = [
        ('owned', 'Owned by Borrower'),
        ('joint_owned', 'Joint Ownership'),
        ('third_party', 'Third Party Owned'),
        ('leased', 'Leased'),
    ]

    # Basic Information
    collateral_id = models.CharField(max_length=20, unique=True, blank=True)
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='collaterals',
        null=True,
        blank=True
    )
    borrower = models.ForeignKey(
        Borrower,
        on_delete=models.PROTECT,
        related_name='collaterals'
    )
    collateral_type = models.ForeignKey(
        CollateralType,
        on_delete=models.PROTECT,
        related_name='collaterals'
    )

    # Description and Details
    title = models.CharField(max_length=200, default="Collateral Item")
    description = models.TextField()
    brand_model = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    year_of_manufacture = models.PositiveIntegerField(null=True, blank=True)
    condition = models.CharField(
        max_length=20,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        default='good'
    )

    # Valuation Information
    estimated_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    market_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    forced_sale_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    valuation_date = models.DateField(default=timezone.now)
    valuation_method = models.CharField(
        max_length=50,
        choices=[
            ('self_declared', 'Self Declared'),
            ('market_comparison', 'Market Comparison'),
            ('professional_appraisal', 'Professional Appraisal'),
            ('cost_approach', 'Cost Approach'),
        ],
        default='self_declared'
    )
    valuated_by = models.CharField(max_length=200, blank=True, null=True)

    # Location and Ownership
    location = models.TextField()
    ownership_status = models.CharField(
        max_length=20,
        choices=OWNERSHIP_STATUS_CHOICES,
        default='owned'
    )
    owner_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="If different from borrower"
    )
    owner_relationship = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Relationship to borrower if third party owned"
    )

    # Legal Information
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    registration_authority = models.CharField(max_length=200, blank=True, null=True)
    legal_title_holder = models.CharField(max_length=200, blank=True, null=True)
    encumbrance_details = models.TextField(
        blank=True,
        null=True,
        help_text="Details of any existing loans, mortgages, or liens"
    )

    # Insurance Information
    is_insured = models.BooleanField(default=False)
    insurance_company = models.CharField(max_length=200, blank=True, null=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    insurance_expiry = models.DateField(null=True, blank=True)

    # Status and Verification
    status = models.CharField(
        max_length=20,
        choices=COLLATERAL_STATUS_CHOICES,
        default='submitted'
    )
    verification_date = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_collaterals'
    )
    verification_notes = models.TextField(blank=True, null=True)

    # Release/Liquidation Information
    release_date = models.DateField(null=True, blank=True)
    released_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_collaterals'
    )
    release_notes = models.TextField(blank=True, null=True)

    liquidation_date = models.DateField(null=True, blank=True)
    liquidation_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    liquidation_method = models.CharField(max_length=200, blank=True, null=True)
    liquidation_notes = models.TextField(blank=True, null=True)

    # Additional Information
    special_conditions = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.collateral_id} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.collateral_id:
            self.collateral_id = self.generate_collateral_id()
        super().save(*args, **kwargs)

    def generate_collateral_id(self):
        """Generate unique collateral ID."""
        last_collateral = Collateral.objects.filter(
            collateral_id__startswith='COL'
        ).order_by('collateral_id').last()

        if last_collateral:
            last_number = int(last_collateral.collateral_id[3:])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"COL{new_number:06d}"

    @property
    def loan_to_value_ratio(self):
        """Calculate loan-to-value ratio if linked to a loan."""
        if self.loan and self.estimated_value > 0:
            return (self.loan.amount_approved / self.estimated_value) * 100
        return Decimal('0.00')

    @property
    def is_adequate_security(self):
        """Check if collateral provides adequate security."""
        if self.loan and self.estimated_value > 0:
            max_ltv = self.collateral_type.loan_to_value_ratio
            current_ltv = self.loan_to_value_ratio
            return current_ltv <= max_ltv
        return True

    @property
    def insurance_status(self):
        """Get insurance status."""
        if not self.is_insured:
            return 'Not Insured'
        elif self.insurance_expiry and self.insurance_expiry < timezone.now().date():
            return 'Insurance Expired'
        else:
            return 'Insured'


def asset_document_upload_path(instance, filename):
    """Generate upload path for asset documents."""
    return f'assets/{instance.asset.asset_id}/documents/{filename}'


def collateral_document_upload_path(instance, filename):
    """Generate upload path for collateral documents."""
    return f'collaterals/{instance.collateral.collateral_id}/documents/{filename}'


class AssetDocument(models.Model):
    """Document management for assets."""

    DOCUMENT_TYPES = [
        ('purchase_invoice', 'Purchase Invoice'),
        ('warranty_card', 'Warranty Card'),
        ('insurance_policy', 'Insurance Policy'),
        ('maintenance_record', 'Maintenance Record'),
        ('valuation_report', 'Valuation Report'),
        ('disposal_certificate', 'Disposal Certificate'),
        ('photo', 'Photograph'),
        ('manual', 'User Manual'),
        ('other', 'Other'),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    document_file = models.FileField(upload_to=asset_document_upload_path)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_asset_documents'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_date']

    def __str__(self):
        return f"{self.asset.asset_id} - {self.title}"

    def save(self, *args, **kwargs):
        if self.document_file:
            self.file_size = self.document_file.size
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        """Get file extension."""
        if self.document_file:
            return os.path.splitext(self.document_file.name)[1].lower()
        return ''

    @property
    def is_image(self):
        """Check if document is an image."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.file_extension in image_extensions


class CollateralDocument(models.Model):
    """Document management for collaterals."""

    DOCUMENT_TYPES = [
        ('ownership_certificate', 'Ownership Certificate'),
        ('title_deed', 'Title Deed'),
        ('registration_certificate', 'Registration Certificate'),
        ('valuation_report', 'Valuation Report'),
        ('insurance_policy', 'Insurance Policy'),
        ('identity_proof', 'Identity Proof'),
        ('address_proof', 'Address Proof'),
        ('income_proof', 'Income Proof'),
        ('photo', 'Photograph'),
        ('survey_report', 'Survey Report'),
        ('legal_opinion', 'Legal Opinion'),
        ('encumbrance_certificate', 'Encumbrance Certificate'),
        ('other', 'Other'),
    ]

    collateral = models.ForeignKey(
        Collateral,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    document_file = models.FileField(upload_to=collateral_document_upload_path)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_collateral_documents'
    )
    is_verified = models.BooleanField(default=False)
    verified_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_collateral_documents'
    )
    verification_notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_date']

    def __str__(self):
        return f"{self.collateral.collateral_id} - {self.title}"

    def save(self, *args, **kwargs):
        if self.document_file:
            self.file_size = self.document_file.size
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        """Get file extension."""
        if self.document_file:
            return os.path.splitext(self.document_file.name)[1].lower()
        return ''

    @property
    def is_image(self):
        """Check if document is an image."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.file_extension in image_extensions


class AssetValuation(models.Model):
    """Asset valuation history tracking."""

    VALUATION_REASONS = [
        ('periodic_review', 'Periodic Review'),
        ('insurance_claim', 'Insurance Claim'),
        ('disposal', 'Disposal'),
        ('impairment_test', 'Impairment Test'),
        ('revaluation', 'Revaluation'),
        ('audit_requirement', 'Audit Requirement'),
        ('other', 'Other'),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='valuations'
    )
    valuation_date = models.DateField()
    valuation_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    valuation_method = models.CharField(
        max_length=50,
        choices=[
            ('market_comparison', 'Market Comparison'),
            ('cost_approach', 'Cost Approach'),
            ('income_approach', 'Income Approach'),
            ('depreciated_replacement_cost', 'Depreciated Replacement Cost'),
        ]
    )
    valuated_by = models.CharField(max_length=200)
    valuation_reason = models.CharField(max_length=30, choices=VALUATION_REASONS)
    notes = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='asset_valuations'
    )

    class Meta:
        ordering = ['-valuation_date']

    def __str__(self):
        return f"{self.asset.asset_id} - {self.valuation_date} - Tsh {self.valuation_value:,.2f}"


class CollateralValuation(models.Model):
    """Collateral valuation history tracking."""

    VALUATION_REASONS = [
        ('initial_assessment', 'Initial Assessment'),
        ('periodic_review', 'Periodic Review'),
        ('loan_restructuring', 'Loan Restructuring'),
        ('liquidation', 'Liquidation'),
        ('insurance_claim', 'Insurance Claim'),
        ('dispute_resolution', 'Dispute Resolution'),
        ('other', 'Other'),
    ]

    collateral = models.ForeignKey(
        Collateral,
        on_delete=models.CASCADE,
        related_name='valuations'
    )
    valuation_date = models.DateField()
    market_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    forced_sale_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    valuation_method = models.CharField(
        max_length=50,
        choices=[
            ('market_comparison', 'Market Comparison'),
            ('professional_appraisal', 'Professional Appraisal'),
            ('cost_approach', 'Cost Approach'),
            ('income_approach', 'Income Approach'),
        ]
    )
    valuated_by = models.CharField(max_length=200)
    valuation_reason = models.CharField(max_length=30, choices=VALUATION_REASONS)
    notes = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collateral_valuations'
    )

    class Meta:
        ordering = ['-valuation_date']

    def __str__(self):
        return f"{self.collateral.collateral_id} - {self.valuation_date} - Tsh {self.market_value:,.2f}"


class AssetDepreciationSchedule(models.Model):
    """Track asset depreciation over time."""

    DEPRECIATION_METHOD = [
        ('straight_line', 'Straight Line'),
        ('declining_balance', 'Declining Balance'),
        ('sum_of_years', 'Sum of Years Digits'),
        ('units_of_production', 'Units of Production'),
    ]

    asset = models.OneToOneField(
        'Asset',
        on_delete=models.CASCADE,
        related_name='depreciation_schedule'
    )

    # Depreciation parameters
    depreciation_method = models.CharField(max_length=20, choices=DEPRECIATION_METHOD)
    useful_life_years = models.PositiveIntegerField()
    salvage_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))]
    )

    # Calculated values
    depreciable_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    annual_depreciation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    accumulated_depreciation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    net_book_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Dates
    depreciation_start_date = models.DateField()
    last_depreciation_date = models.DateField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_depreciation_schedules'
    )

    class Meta:
        ordering = ['-depreciation_start_date']

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.get_depreciation_method_display()}"

    def save(self, *args, **kwargs):
        # Calculate depreciable amount
        self.depreciable_amount = self.asset.purchase_price - self.salvage_value

        # Calculate annual depreciation based on method
        if self.depreciation_method == 'straight_line':
            if self.useful_life_years > 0:
                self.annual_depreciation = self.depreciable_amount / self.useful_life_years
        elif self.depreciation_method == 'declining_balance' and self.depreciation_rate:
            self.annual_depreciation = self.net_book_value * (self.depreciation_rate / 100)

        # Calculate net book value
        self.net_book_value = self.asset.purchase_price - self.accumulated_depreciation

        super().save(*args, **kwargs)

    def calculate_current_depreciation(self):
        """Calculate current accumulated depreciation."""
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta

        if not self.is_active:
            return self.accumulated_depreciation

        current_date = timezone.now().date()
        months_elapsed = relativedelta(current_date, self.depreciation_start_date).months
        years_elapsed = months_elapsed / 12

        if self.depreciation_method == 'straight_line':
            total_depreciation = min(
                self.annual_depreciation * years_elapsed,
                self.depreciable_amount
            )
        else:
            # For other methods, use straight line as default
            total_depreciation = min(
                self.annual_depreciation * years_elapsed,
                self.depreciable_amount
            )

        self.accumulated_depreciation = total_depreciation
        self.net_book_value = self.asset.purchase_price - self.accumulated_depreciation
        self.save()

        return self.accumulated_depreciation


class CollateralRiskAssessment(models.Model):
    """Assess and track collateral risk factors."""

    RISK_LEVEL = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('very_high', 'Very High Risk'),
    ]

    RISK_FACTOR = [
        ('market_volatility', 'Market Volatility'),
        ('liquidity', 'Liquidity Risk'),
        ('physical_condition', 'Physical Condition'),
        ('legal_issues', 'Legal Issues'),
        ('location', 'Location Risk'),
        ('obsolescence', 'Obsolescence Risk'),
        ('maintenance', 'Maintenance Requirements'),
        ('insurance', 'Insurance Coverage'),
    ]

    collateral = models.ForeignKey(
        'Collateral',
        on_delete=models.CASCADE,
        related_name='risk_assessments'
    )

    # Assessment details
    assessment_date = models.DateField(default=timezone.now)
    assessed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collateral_risk_assessments'
    )

    # Overall risk
    overall_risk_level = models.CharField(max_length=20, choices=RISK_LEVEL)
    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )

    # Risk factors
    market_volatility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    liquidity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    condition_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    legal_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )

    # Risk mitigation
    mitigation_measures = models.TextField(blank=True, null=True)
    recommended_actions = models.TextField(blank=True, null=True)

    # Review information
    next_review_date = models.DateField(null=True, blank=True)
    review_frequency_months = models.PositiveIntegerField(default=12)

    # Notes
    assessment_notes = models.TextField(blank=True, null=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assessment_date']

    def __str__(self):
        return f"{self.collateral.collateral_id} - {self.assessment_date} - {self.overall_risk_level}"

    def save(self, *args, **kwargs):
        # Calculate overall risk score
        scores = [
            self.market_volatility_score,
            self.liquidity_score,
            self.condition_score,
            self.legal_score
        ]
        self.risk_score = sum(scores) / len(scores)

        # Determine risk level based on score
        if self.risk_score <= 25:
            self.overall_risk_level = 'low'
        elif self.risk_score <= 50:
            self.overall_risk_level = 'medium'
        elif self.risk_score <= 75:
            self.overall_risk_level = 'high'
        else:
            self.overall_risk_level = 'very_high'

        # Set next review date
        if not self.next_review_date:
            from dateutil.relativedelta import relativedelta
            self.next_review_date = self.assessment_date + relativedelta(months=self.review_frequency_months)

        super().save(*args, **kwargs)


class AssetMaintenanceSchedule(models.Model):
    """Schedule and track asset maintenance activities."""

    MAINTENANCE_TYPE = [
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Corrective Maintenance'),
        ('emergency', 'Emergency Maintenance'),
        ('inspection', 'Inspection'),
        ('calibration', 'Calibration'),
    ]

    MAINTENANCE_STATUS = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('overdue', 'Overdue'),
    ]

    FREQUENCY = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('as_needed', 'As Needed'),
    ]

    maintenance_id = models.CharField(max_length=20, unique=True, blank=True)
    asset = models.ForeignKey(
        'Asset',
        on_delete=models.CASCADE,
        related_name='maintenance_schedules'
    )

    # Maintenance details
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Scheduling
    frequency = models.CharField(max_length=20, choices=FREQUENCY)
    scheduled_date = models.DateField()
    estimated_duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.1'))]
    )

    # Execution
    actual_start_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    actual_duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.1'))]
    )

    # Personnel
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_maintenance'
    )
    performed_by = models.CharField(max_length=200, blank=True, null=True)

    # Costs
    estimated_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    actual_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Status and completion
    status = models.CharField(max_length=20, choices=MAINTENANCE_STATUS, default='scheduled')
    completion_notes = models.TextField(blank=True, null=True)
    parts_replaced = models.TextField(blank=True, null=True)

    # Next maintenance
    next_maintenance_date = models.DateField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_maintenance_schedules'
    )

    class Meta:
        ordering = ['scheduled_date']

    def __str__(self):
        return f"{self.maintenance_id} - {self.asset.asset_tag} - {self.title}"

    def save(self, *args, **kwargs):
        # Generate maintenance ID
        if not self.maintenance_id:
            last_maintenance = AssetMaintenanceSchedule.objects.filter(
                maintenance_id__startswith='MNT'
            ).order_by('maintenance_id').last()

            if last_maintenance:
                last_number = int(last_maintenance.maintenance_id[3:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.maintenance_id = f"MNT{new_number:06d}"

        # Update status based on dates
        from django.utils import timezone
        current_date = timezone.now().date()

        if self.status == 'scheduled' and self.scheduled_date < current_date:
            self.status = 'overdue'
        elif self.actual_start_date and not self.actual_completion_date:
            self.status = 'in_progress'
        elif self.actual_completion_date:
            self.status = 'completed'

        # Calculate next maintenance date
        if self.status == 'completed' and not self.next_maintenance_date:
            from dateutil.relativedelta import relativedelta

            if self.frequency == 'monthly':
                self.next_maintenance_date = self.actual_completion_date + relativedelta(months=1)
            elif self.frequency == 'quarterly':
                self.next_maintenance_date = self.actual_completion_date + relativedelta(months=3)
            elif self.frequency == 'semi_annual':
                self.next_maintenance_date = self.actual_completion_date + relativedelta(months=6)
            elif self.frequency == 'annual':
                self.next_maintenance_date = self.actual_completion_date + relativedelta(years=1)

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if maintenance is overdue."""
        from django.utils import timezone
        return self.scheduled_date < timezone.now().date() and self.status in ['scheduled', 'in_progress']

    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.is_overdue:
            from django.utils import timezone
            delta = timezone.now().date() - self.scheduled_date
            return delta.days
        return 0


