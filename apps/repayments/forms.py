"""
Forms for repayment and payment processing.
"""
from django import forms
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from .models import (
    Payment, LoanRepaymentSchedule, PaymentAllocation, PaymentStatus,
    DailyCollection, CollectionSummary
)
from apps.loans.models import Loan
from apps.borrowers.models import Borrower
from apps.core.models import PaymentMethodChoices


class PaymentForm(forms.ModelForm):
    """Form for processing payments."""
    
    class Meta:
        model = Payment
        fields = [
            'loan', 'amount', 'payment_method', 'payment_date', 'payment_type',
            'receipt_number', 'transaction_id', 'external_reference', 'notes'
        ]
        
        widgets = {
            'loan': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_loan'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter payment amount',
                'required': True,
                'id': 'id_amount'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'payment_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'receipt_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter receipt number (optional)'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter transaction ID (optional)'
            }),
            'external_reference': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter external reference (optional)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter payment notes...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['loan'].label = 'Loan'
        self.fields['amount'].label = 'Payment Amount (Tsh)'
        self.fields['payment_method'].label = 'Payment Method'
        self.fields['payment_date'].label = 'Payment Date'
        self.fields['payment_type'].label = 'Payment Type'
        self.fields['receipt_number'].label = 'Receipt Number'
        self.fields['transaction_id'].label = 'Transaction ID'
        self.fields['external_reference'].label = 'External Reference'
        self.fields['notes'].label = 'Notes'
        
        # Set default values
        if not self.instance.pk:
            self.fields['payment_date'].initial = timezone.now().date()
        
        # Filter active loans
        self.fields['loan'].queryset = Loan.objects.filter(
            status__in=['active', 'overdue']
        ).select_related('borrower').order_by('loan_number')
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Payment amount must be greater than zero.')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        loan = cleaned_data.get('loan')
        amount = cleaned_data.get('amount')
        payment_date = cleaned_data.get('payment_date')
        
        if loan and amount:
            # Check if loan has outstanding balance
            if loan.outstanding_balance <= 0:
                raise forms.ValidationError('This loan has no outstanding balance.')
            
            # Warn if payment exceeds outstanding balance
            if amount > loan.outstanding_balance:
                # This is allowed (advance payment) but we'll show a warning
                pass
        
        if payment_date and payment_date > timezone.now().date():
            raise forms.ValidationError('Payment date cannot be in the future.')
        
        return cleaned_data


class BulkPaymentForm(forms.Form):
    """Form for processing bulk payments."""
    
    payment_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': '.csv,.xlsx,.xls',
            'required': True
        }),
        label='Payment File',
        help_text='Upload CSV or Excel file with payment data'
    )
    
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        label='Payment Date',
        initial=timezone.now().date()
    )
    
    payment_method = forms.ChoiceField(
        choices=PaymentMethodChoices.choices,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Payment Method'
    )
    
    validate_only = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Validate Only (Don\'t Process)',
        required=False,
        help_text='Check to validate file without processing payments'
    )
    
    def clean_payment_file(self):
        file = self.cleaned_data.get('payment_file')
        if file:
            # Validate file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')
            
            # Validate file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError('Only CSV and Excel files are allowed.')
        
        return file


class PaymentAllocationForm(forms.ModelForm):
    """Form for manual payment allocation."""
    
    class Meta:
        model = PaymentAllocation
        fields = [
            'installment', 'principal_allocated', 'interest_allocated',
            'penalty_allocated', 'fees_allocated'
        ]
        
        widgets = {
            'installment': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'principal_allocated': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter principal amount'
            }),
            'interest_allocated': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter interest amount'
            }),
            'penalty_allocated': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter penalty amount'
            }),
            'fees_allocated': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter fees amount'
            }),
        }
    
    def __init__(self, payment=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if payment:
            # Filter installments for this payment's loan
            self.fields['installment'].queryset = payment.loan.repayment_schedule.filter(
                payment_status__in=['pending', 'partial', 'overdue']
            ).order_by('installment_number')
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate allocation amounts
        principal = cleaned_data.get('principal_allocated', Decimal('0.00'))
        interest = cleaned_data.get('interest_allocated', Decimal('0.00'))
        penalty = cleaned_data.get('penalty_allocated', Decimal('0.00'))
        fees = cleaned_data.get('fees_allocated', Decimal('0.00'))
        
        total_allocated = principal + interest + penalty + fees
        
        if total_allocated <= 0:
            raise forms.ValidationError('At least one allocation amount must be greater than zero.')
        
        # Check against installment outstanding amounts
        installment = cleaned_data.get('installment')
        if installment:
            if principal > installment.outstanding_principal:
                raise forms.ValidationError(f'Principal allocation exceeds outstanding amount (Tsh {installment.outstanding_principal})')
            
            if interest > installment.outstanding_interest:
                raise forms.ValidationError(f'Interest allocation exceeds outstanding amount (Tsh {installment.outstanding_interest})')
            
            if penalty > installment.outstanding_penalty:
                raise forms.ValidationError(f'Penalty allocation exceeds outstanding amount (Tsh {installment.outstanding_penalty})')
            
            if fees > installment.outstanding_fees:
                raise forms.ValidationError(f'Fees allocation exceeds outstanding amount (Tsh {installment.outstanding_fees})')
        
        return cleaned_data


class PaymentReversalForm(forms.Form):
    """Form for reversing payments."""
    
    payment = forms.ModelChoiceField(
        queryset=Payment.objects.filter(
            status=PaymentStatus.COMPLETED,
            is_reversed=False
        ),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Payment to Reverse'
    )
    
    reversal_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Enter reason for payment reversal...',
            'required': True
        }),
        label='Reversal Reason',
        max_length=500
    )
    
    confirm_reversal = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'required': True
        }),
        label='I confirm that I want to reverse this payment',
        help_text='This action cannot be undone'
    )
    
    def __init__(self, loan=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if loan:
            # Filter payments for specific loan
            self.fields['payment'].queryset = Payment.objects.filter(
                loan=loan,
                status=PaymentStatus.COMPLETED,
                is_reversed=False
            ).order_by('-payment_date')


class ScheduleAdjustmentForm(forms.ModelForm):
    """Form for adjusting repayment schedule."""
    
    class Meta:
        model = LoanRepaymentSchedule
        fields = [
            'due_date', 'principal_amount', 'interest_amount', 'penalty_amount',
            'fees_amount', 'adjustment_reason'
        ]
        
        widgets = {
            'due_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'principal_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'required': True
            }),
            'interest_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'required': True
            }),
            'penalty_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00'
            }),
            'fees_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00'
            }),
            'adjustment_reason': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter reason for schedule adjustment...',
                'required': True
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate that amounts are reasonable
        principal = cleaned_data.get('principal_amount', Decimal('0.00'))
        interest = cleaned_data.get('interest_amount', Decimal('0.00'))
        
        if principal + interest <= 0:
            raise forms.ValidationError('Principal and interest amounts cannot both be zero.')
        
        return cleaned_data


# =============================================================================
# DAILY COLLECTION FORMS
# =============================================================================

class DailyCollectionForm(forms.ModelForm):
    """Form for creating and editing daily collections."""

    class Meta:
        model = DailyCollection
        fields = [
            'collection_date', 'collector', 'target_amount', 'target_payments',
            'collection_start_time', 'collection_end_time', 'collection_route',
            'collection_area', 'travel_distance_km', 'notes'
        ]

        widgets = {
            'collection_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'collector': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter target collection amount'
            }),
            'target_payments': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'placeholder': 'Enter target number of payments'
            }),
            'collection_start_time': forms.TimeInput(attrs={
                'class': 'form-input',
                'type': 'time'
            }),
            'collection_end_time': forms.TimeInput(attrs={
                'class': 'form-input',
                'type': 'time'
            }),
            'collection_route': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter collection route/area'
            }),
            'collection_area': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter collection area'
            }),
            'travel_distance_km': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.1',
                'min': '0.0',
                'placeholder': 'Enter travel distance in km'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter collection notes...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set field labels
        self.fields['collection_date'].label = 'Collection Date'
        self.fields['collector'].label = 'Collector'
        self.fields['target_amount'].label = 'Target Amount (Tsh)'
        self.fields['target_payments'].label = 'Target Payments'
        self.fields['collection_start_time'].label = 'Start Time'
        self.fields['collection_end_time'].label = 'End Time'
        self.fields['collection_route'].label = 'Collection Route'
        self.fields['collection_area'].label = 'Collection Area'
        self.fields['travel_distance_km'].label = 'Travel Distance (km)'
        self.fields['notes'].label = 'Notes'

        # Filter active collectors
        from apps.accounts.models import CustomUser
        self.fields['collector'].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')

        # Set default values
        if not self.instance.pk:
            self.fields['collection_date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        collection_date = cleaned_data.get('collection_date')
        collector = cleaned_data.get('collector')
        start_time = cleaned_data.get('collection_start_time')
        end_time = cleaned_data.get('collection_end_time')

        # Check for duplicate collection entry
        if collection_date and collector:
            existing = DailyCollection.objects.filter(
                collection_date=collection_date,
                collector=collector
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    f'Collection entry already exists for {collector.get_full_name()} on {collection_date}'
                )

        # Validate time range
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError('End time must be after start time.')

        # Validate collection date
        if collection_date and collection_date > timezone.now().date():
            raise forms.ValidationError('Collection date cannot be in the future.')

        return cleaned_data


class CollectionValidationForm(forms.Form):
    """Form for validating collections."""

    ACTION_CHOICES = [
        ('validate', 'Validate Collection'),
        ('approve', 'Approve Collection'),
        ('reject', 'Reject Collection'),
        ('resolve_discrepancy', 'Resolve Discrepancy'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Action'
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Enter validation notes...'
        }),
        label='Notes',
        required=False,
        max_length=500
    )

    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Enter rejection reason...'
        }),
        label='Rejection Reason',
        required=False,
        max_length=500
    )

    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Enter resolution notes...'
        }),
        label='Resolution Notes',
        required=False,
        max_length=500
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reason = cleaned_data.get('reason')
        resolution_notes = cleaned_data.get('resolution_notes')

        if action == 'reject' and not reason:
            raise forms.ValidationError('Rejection reason is required when rejecting a collection.')

        if action == 'resolve_discrepancy' and not resolution_notes:
            raise forms.ValidationError('Resolution notes are required when resolving discrepancies.')

        return cleaned_data


class CollectionTargetForm(forms.Form):
    """Form for setting collection targets."""

    target_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        label='Target Date'
    )

    collectors = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox-list'
        }),
        label='Select Collectors',
        required=True
    )

    target_amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Enter target amount per collector',
            'required': True
        }),
        label='Target Amount per Collector (Tsh)',
        min_value=Decimal('0.01')
    )

    target_payments = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'min': '1',
            'placeholder': 'Enter target payments per collector'
        }),
        label='Target Payments per Collector',
        min_value=1,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter active collectors
        from apps.accounts.models import CustomUser
        self.fields['collectors'].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')

        # Set default date
        self.fields['target_date'].initial = timezone.now().date()


class CollectionSearchForm(forms.Form):
    """Form for searching collections."""

    search_query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by collector name...'
        }),
        label='Search',
        required=False
    )

    collection_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='Collection Date',
        required=False
    )

    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='From Date',
        required=False
    )

    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='To Date',
        required=False
    )

    collector = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Collector',
        required=False,
        empty_label='All Collectors'
    )

    validation_status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + DailyCollection._meta.get_field('validation_status').choices,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Validation Status',
        required=False
    )

    has_discrepancy = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('yes', 'With Discrepancy'),
            ('no', 'No Discrepancy')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Discrepancy Status',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter collectors who have made collections
        from apps.accounts.models import CustomUser
        self.fields['collector'].queryset = CustomUser.objects.filter(
            daily_collections__isnull=False
        ).distinct().order_by('first_name', 'last_name')

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('From date cannot be after to date.')

        return cleaned_data


class BulkCollectionImportForm(forms.Form):
    """Form for importing bulk collection data."""

    import_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': '.csv,.xlsx,.xls',
            'required': True
        }),
        label='Collection Data File',
        help_text='Upload CSV or Excel file with collection data'
    )

    collection_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        label='Collection Date',
        initial=timezone.now().date()
    )

    update_existing = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Update Existing Collections',
        required=False,
        help_text='Check to update existing collection records'
    )

    validate_only = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Validate Only (Don\'t Import)',
        required=False,
        help_text='Check to validate file without importing data'
    )

    def clean_import_file(self):
        file = self.cleaned_data.get('import_file')
        if file:
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 5MB.')

            # Validate file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError('Only CSV and Excel files are allowed.')

        return file


class PaymentSearchForm(forms.Form):
    """Form for searching payments."""
    
    search_query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by payment reference, loan number, or borrower name...'
        }),
        label='Search',
        required=False
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + PaymentStatus.choices,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Status',
        required=False
    )
    
    payment_method = forms.ChoiceField(
        choices=[('', 'All Methods')] + PaymentMethodChoices.choices,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Payment Method',
        required=False
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='From Date',
        required=False
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='To Date',
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('From date cannot be after to date.')
        
        return cleaned_data
