from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import (
    Loan, GroupLoan, RepaymentSchedule, Repayment, 
    Penalty, WrittenOffLoan, OldLoan, LoanDisbursement,
    PaymentMethodChoices, RepaymentTypeChoices
)
from apps.borrowers.models import Borrower, BorrowerGroup
from apps.core.models import LoanStatusChoices, FrequencyChoices
from apps.accounts.models import CustomUser


class ComprehensiveLoanForm(forms.ModelForm):
    """Enhanced form for creating loans with all new fields."""

    interest_amount = forms.DecimalField(
        min_value=Decimal('0.00'),
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter total interest amount (TZS)',
            'required': True,
        }),
        label='Interest Amount (TZS)'
    )
    
    # Loan category choices
    LOAN_CATEGORY_CHOICES = [
        ('', 'Select loan category'),
        ('asset', 'Asset Loans'),
        ('individual', 'Individual Loans'),
        ('emergency', 'Emergency Loans'),
    ]
    
    class Meta:
        model = Loan
        fields = [
            'borrower', 'loan_category', 'amount_requested',
            'duration_months', 'proposed_project', 'collateral_name', 
            'collateral_worth', 'collateral_withheld', 'application_date',
            'loan_officer', 'pay_method', 'payment_account', 'start_payment_date',
            'repayment_type', 'repayment_frequency', 'loan_fees_applied', 'supporting_document', 'notes'
        ]
        widgets = {
            'borrower': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'loan_category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount_requested': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '1000',
                'max': '50000000',
                'placeholder': 'Enter loan amount (TZS)',
                'required': True
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60',
                'placeholder': 'Enter duration in months',
                'required': True
            }),
            'proposed_project': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Brief description of the intended use',
                'required': True
            }),
            'collateral_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Land title, Vehicle, Equipment',
            }),
            'collateral_worth': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Estimated market value (TZS)',
            }),
            'collateral_withheld': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Amount to be withheld (TZS)',
            }),
            'application_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'loan_officer': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Name of loan officer',
            }),
            'pay_method': forms.Select(choices=PaymentMethodChoices.choices, attrs={
                'class': 'form-select',
                'required': True
            }),
            'payment_account': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Account number or mobile money number',
            }),
            'start_payment_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'repayment_type': forms.Select(choices=RepaymentTypeChoices.choices, attrs={
                'class': 'form-select',
                'required': True
            }),
            'repayment_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'supporting_document': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Additional notes or observations about this loan application...'
            }),
        }

    # Additional field for loan fees radio button
    loan_fees = forms.ChoiceField(
        choices=[('yes', 'Yes'), ('no', 'No')],
        widget=forms.RadioSelect(),
        required=True,
        label="Apply loan processing fees?"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['borrower'].queryset = Borrower.objects.filter(status='active')
        self.fields['application_date'].required = True
        self.fields['application_date'].initial = timezone.now().date()
        self.fields['start_payment_date'].required = False
        self.fields['start_payment_date'].widget.attrs.pop('required', None)
        # Make borrower field required
        self.fields['borrower'].required = True
        
        # Ensure critical fields are required
        self.fields['amount_requested'].required = True
        self.fields['interest_amount'].required = True
        self.fields['duration_months'].required = True
        self.fields['repayment_type'].required = True
        
        # Set the choices for loan_category field
        self.fields['loan_category'] = forms.ChoiceField(
            choices=self.LOAN_CATEGORY_CHOICES,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            required=True
        )
        
        # Set repayment_frequency field choices to use the latest FrequencyChoices
        self.fields['repayment_frequency'].widget.choices = FrequencyChoices.choices
        
        # When editing an existing loan, populate interest_amount from total_interest
        if self.instance and self.instance.pk:
            # If editing, populate interest_amount with existing total_interest
            if self.instance.total_interest:
                self.fields['interest_amount'].initial = self.instance.total_interest
            # Set loan_fees initial value based on loan_fees_applied
            self.fields['loan_fees'].initial = 'yes' if self.instance.loan_fees_applied else 'no'
        
        # Set field labels
        self.fields['borrower'].label = 'Borrower'
        self.fields['loan_category'].label = 'Loan Category'
        self.fields['amount_requested'].label = 'Loan Amount (TZS)'
        self.fields['interest_amount'].label = 'Interest Amount (TZS)'
        self.fields['duration_months'].label = 'Loan Duration (Months)'
        self.fields['proposed_project'].label = 'Purpose of Loan'
        self.fields['collateral_name'].label = 'Collateral Description'
        self.fields['collateral_worth'].label = 'Collateral Worth (TZS)'
        self.fields['collateral_withheld'].label = 'Amount Withheld (TZS)'
        self.fields['application_date'].label = 'Application Date'
        self.fields['loan_officer'].label = 'Loan Officer'
        self.fields['pay_method'].label = 'Payment Method'
        self.fields['payment_account'].label = 'Payment Account'
        self.fields['start_payment_date'].label = 'Start Payment Date'
        self.fields['repayment_type'].label = 'Repayment Type'
        self.fields['repayment_frequency'].label = 'Repayment Frequency (Interval)'
        self.fields['supporting_document'].label = 'Supporting Document'
        self.fields['notes'].label = 'Additional Notes'

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate collateral amounts
        collateral_worth = cleaned_data.get('collateral_worth')
        collateral_withheld = cleaned_data.get('collateral_withheld')
        
        if collateral_worth and collateral_withheld:
            if collateral_withheld > collateral_worth:
                raise ValidationError('Amount withheld cannot be greater than collateral worth')
        
        # Validate dates
        application_date = cleaned_data.get('application_date')
        start_payment_date = cleaned_data.get('start_payment_date')
        
        if application_date and start_payment_date:
            if start_payment_date <= application_date:
                raise ValidationError('Start payment date must be after application date')
        
        # Check backdating setting from WorkingMode
        if application_date:
            from apps.core.models import WorkingMode
            working_mode = WorkingMode.get_active_mode()
            
            # If backdating is not allowed and date is in the past, raise error
            if working_mode and not working_mode.allow_backdating:
                today = timezone.now().date()
                if application_date < today:
                    raise ValidationError(
                        'Backdating is not allowed. Application date cannot be earlier than today.'
                    )
        
        # Validate payment account for non-cash methods
        pay_method = cleaned_data.get('pay_method')
        payment_account = cleaned_data.get('payment_account')
        
        if pay_method in [PaymentMethodChoices.MOBILE_MONEY, PaymentMethodChoices.BANK_TRANSFER]:
            if not payment_account or not payment_account.strip():
                raise ValidationError(f'Payment account is required for {pay_method}')
        
        return cleaned_data

    def clean_supporting_document(self):
        document = self.cleaned_data.get('supporting_document')
        if document:
            # Check file size (10MB limit)
            if document.size > 10 * 1024 * 1024:
                raise ValidationError('File size must not exceed 10MB')
            
            # Check file type
            allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
            if document.content_type not in allowed_types:
                raise ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed')
        
        return document

    def save(self, commit=True):
        instance = super().save(commit=False)

        interest_amount = self.cleaned_data.get('interest_amount') or Decimal('0.00')
        principal = self.cleaned_data.get('amount_requested') or Decimal('0.00')
        duration_months = self.cleaned_data.get('duration_months') or 0

        # Keep compatibility with existing reports that still use interest_rate.
        if principal > 0 and duration_months > 0:
            derived_rate = (interest_amount / principal) * (Decimal('12') / Decimal(str(duration_months))) * Decimal('100')
            instance.interest_rate = derived_rate.quantize(Decimal('0.01'))
        else:
            instance.interest_rate = Decimal('0.00')

        # Persist requested manual interest via model save hook.
        instance._manual_interest_amount = interest_amount
        
        # Set loan_fees_applied based on radio button choice
        loan_fees_choice = self.cleaned_data.get('loan_fees')
        instance.loan_fees_applied = (loan_fees_choice == 'yes')
        
        if commit:
            instance.save()
        return instance
    
    def _post_clean(self):
        """Skip validation on system-managed date fields."""
        try:
            super()._post_clean()
        except forms.ValidationError as e:
            # Only re-raise errors for fields that are in this form
            if hasattr(e, 'error_dict'):
                filtered_errors = {
                    field: errors for field, errors in e.error_dict.items()
                    if field in self.fields
                }
                if filtered_errors:
                    raise forms.ValidationError(filtered_errors)


class LoanForm(forms.ModelForm):
    """Form for creating and editing individual loans."""
    
    class Meta:
        model = Loan
        fields = [
            'borrower', 'amount_requested', 'interest_rate',
            'duration_months', 'repayment_frequency', 'application_notes'
        ]
        widgets = {
            'borrower': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount_requested': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter loan amount',
                'required': True
            }),
            'interest_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'Enter interest rate (%)',
                'required': True
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60',
                'placeholder': 'Enter duration in months',
                'required': True
            }),
            'repayment_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'application_notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about the loan application...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['borrower'].queryset = Borrower.objects.filter(status='active')

        # Set repayment_frequency field choices dynamically
        self.fields['repayment_frequency'].widget.choices = FrequencyChoices.choices

        # Set field labels
        self.fields['borrower'].label = 'Select Borrower'
        self.fields['amount_requested'].label = 'Loan Amount'
        self.fields['interest_rate'].label = 'Interest Rate (%)'
        self.fields['duration_months'].label = 'Duration (Months)'
        self.fields['repayment_frequency'].label = 'Repayment Frequency'
        self.fields['application_notes'].label = 'Application Notes'

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class ComprehensiveGroupLoanForm(forms.ModelForm):
    """Enhanced form for creating group loans with comprehensive fields."""

    interest_amount = forms.DecimalField(
        min_value=Decimal('0.00'),
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter total interest amount (TZS)',
            'required': True,
        }),
        label='Interest Amount (TZS)'
    )
    
    # Loan category choices
    LOAN_CATEGORY_CHOICES = [
        ('', 'Select loan category'),
        ('business', 'Business Loan'),
        ('agriculture', 'Agriculture Loan'),
        ('education', 'Education Loan'),
        ('emergency', 'Emergency Loan'),
        ('housing', 'Housing Loan'),
        ('other', 'Other'),
    ]
    
    class Meta:
        model = Loan
        fields = [
            'loan_category', 'amount_requested',
            'duration_months', 'proposed_project', 'collateral_name', 
            'collateral_worth', 'collateral_withheld', 'application_date',
            'loan_officer', 'pay_method', 'payment_account', 'start_payment_date',
            'repayment_type', 'repayment_frequency', 'loan_fees_applied', 'supporting_document', 'notes'
        ]
        widgets = {
            'loan_category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount_requested': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '10000',
                'max': '100000000',
                'placeholder': 'Enter group loan amount (TZS)',
                'required': True
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60',
                'placeholder': 'Enter duration in months',
                'required': True
            }),
            'proposed_project': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Brief description of the intended use for the group',
                'required': True
            }),
            'collateral_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Group assets, member guarantees',
            }),
            'collateral_worth': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Estimated total collateral value (TZS)',
            }),
            'collateral_withheld': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Amount to be withheld (TZS)',
            }),
            'application_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'loan_officer': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Name of loan officer',
            }),
            'pay_method': forms.Select(choices=PaymentMethodChoices.choices, attrs={
                'class': 'form-select',
                'required': True
            }),
            'payment_account': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Group leader account or group account',
            }),
            'start_payment_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'repayment_type': forms.Select(choices=RepaymentTypeChoices.choices, attrs={
                'class': 'form-select',
                'required': True
            }),
            'repayment_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'supporting_document': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Additional notes about this group loan application...'
            }),
        }

    # Group selection field
    group = forms.ModelChoiceField(
        queryset=BorrowerGroup.objects.filter(status='active'),
        widget=forms.HiddenInput(),
        required=True,
        label="Borrower Group"
    )

    # Additional field for loan fees radio button
    loan_fees = forms.ChoiceField(
        choices=[('yes', 'Yes'), ('no', 'No')],
        widget=forms.RadioSelect(),
        required=True,
        label="Apply loan processing fees?"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['application_date'].required = True
        self.fields['application_date'].initial = timezone.now().date()
        self.fields['start_payment_date'].required = False
        self.fields['start_payment_date'].widget.attrs.pop('required', None)
        
        # Set the choices for loan_category field
        self.fields['loan_category'] = forms.ChoiceField(
            choices=self.LOAN_CATEGORY_CHOICES,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            required=True
        )
        
        # Update repayment_frequency field choices to use the latest FrequencyChoices
        self.fields['repayment_frequency'].widget.choices = FrequencyChoices.choices
        
        # Set field labels
        self.fields['group'].label = 'Borrower Group'
        self.fields['loan_category'].label = 'Loan Category'
        self.fields['amount_requested'].label = 'Group Loan Amount (TZS)'
        self.fields['interest_amount'].label = 'Interest Amount (TZS)'
        self.fields['duration_months'].label = 'Loan Duration (Months)'
        self.fields['proposed_project'].label = 'Purpose of Group Loan'
        self.fields['collateral_name'].label = 'Group Collateral Description'
        self.fields['collateral_worth'].label = 'Total Collateral Worth (TZS)'
        self.fields['collateral_withheld'].label = 'Amount Withheld (TZS)'
        self.fields['application_date'].label = 'Application Date'
        self.fields['loan_officer'].label = 'Loan Officer'
        self.fields['pay_method'].label = 'Payment Method'
        self.fields['payment_account'].label = 'Payment Account'
        self.fields['start_payment_date'].label = 'Start Payment Date'
        self.fields['repayment_type'].label = 'Repayment Type'
        self.fields['repayment_frequency'].label = 'Repayment Frequency (Interval)'
        self.fields['supporting_document'].label = 'Supporting Document'
        self.fields['notes'].label = 'Additional Notes'

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate collateral amounts
        collateral_worth = cleaned_data.get('collateral_worth')
        collateral_withheld = cleaned_data.get('collateral_withheld')
        
        if collateral_worth and collateral_withheld:
            if collateral_withheld > collateral_worth:
                raise ValidationError('Amount withheld cannot be greater than collateral worth')
        
        # Validate dates
        application_date = cleaned_data.get('application_date')
        start_payment_date = cleaned_data.get('start_payment_date')
        
        if application_date and start_payment_date:
            if start_payment_date <= application_date:
                raise ValidationError('Start payment date must be after application date')
        
        # Check backdating setting from WorkingMode
        if application_date:
            from apps.core.models import WorkingMode
            working_mode = WorkingMode.get_active_mode()
            
            # If backdating is not allowed and date is in the past, raise error
            if working_mode and not working_mode.allow_backdating:
                today = timezone.now().date()
                if application_date < today:
                    raise ValidationError(
                        'Backdating is not allowed. Application date cannot be earlier than today.'
                    )
        
        # Validate payment account for non-cash methods
        pay_method = cleaned_data.get('pay_method')
        payment_account = cleaned_data.get('payment_account')
        
        if pay_method in [PaymentMethodChoices.MOBILE_MONEY, PaymentMethodChoices.BANK_TRANSFER]:
            if not payment_account or not payment_account.strip():
                raise ValidationError(f'Payment account is required for {pay_method}')
        
        return cleaned_data

    def clean_supporting_document(self):
        document = self.cleaned_data.get('supporting_document')
        if document:
            # Check file size (10MB limit)
            if document.size > 10 * 1024 * 1024:
                raise ValidationError('File size must not exceed 10MB')
            
            # Check file type
            allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
            if document.content_type not in allowed_types:
                raise ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed')
        
        return document

    def save(self, commit=True):
        instance = super().save(commit=False)

        interest_amount = self.cleaned_data.get('interest_amount') or Decimal('0.00')
        principal = self.cleaned_data.get('amount_requested') or Decimal('0.00')
        duration_months = self.cleaned_data.get('duration_months') or 0

        if principal > 0 and duration_months > 0:
            derived_rate = (interest_amount / principal) * (Decimal('12') / Decimal(str(duration_months))) * Decimal('100')
            instance.interest_rate = derived_rate.quantize(Decimal('0.01'))
        else:
            instance.interest_rate = Decimal('0.00')

        instance._manual_interest_amount = interest_amount
        
        # Set loan_fees_applied based on radio button choice
        loan_fees_choice = self.cleaned_data.get('loan_fees')
        instance.loan_fees_applied = (loan_fees_choice == 'yes')
        
        # Set the borrower to the group leader
        group = self.cleaned_data.get('group')
        if group and hasattr(group, 'leader'):
            instance.borrower = group.leader
        elif group:
            # If no leader, use the first member
            instance.borrower = group.members.first()
        
        if commit:
            instance.save()
        return instance


class GroupLoanForm(forms.ModelForm):
    """Form for creating group loans."""
    
    class Meta:
        model = Loan
        fields = [
            'amount_requested', 'interest_rate',
            'duration_months', 'repayment_frequency', 'application_notes'
        ]
        widgets = {
            'amount_requested': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter loan amount',
                'required': True
            }),
            'interest_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'Enter interest rate (%)',
                'required': True
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60',
                'placeholder': 'Enter duration in months',
                'required': True
            }),
            'repayment_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'application_notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about the group loan application...'
            }),
        }

    group = forms.ModelChoiceField(
        queryset=BorrowerGroup.objects.filter(status='active'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        empty_label="Select Borrower Group"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update repayment_frequency field choices to use the latest FrequencyChoices
        self.fields['repayment_frequency'].widget.choices = FrequencyChoices.choices

        # Set field labels
        self.fields['group'].label = 'Select Borrower Group'
        self.fields['amount_requested'].label = 'Loan Amount'
        self.fields['interest_rate'].label = 'Interest Rate (%)'
        self.fields['duration_months'].label = 'Duration (Months)'
        self.fields['repayment_frequency'].label = 'Repayment Frequency'
        self.fields['application_notes'].label = 'Application Notes'


class RepaymentForm(forms.ModelForm):
    """Form for recording individual repayments."""
    
    class Meta:
        model = Repayment
        fields = ['amount_paid', 'payment_date']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter payment amount',
                'required': True
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
        }

    def __init__(self, *args, schedule=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.schedule = schedule
        if schedule:
            self.fields['amount_paid'].widget.attrs['placeholder'] = f'Due: {schedule.amount_due}'

    def clean_amount_paid(self):
        amount_paid = self.cleaned_data.get('amount_paid')
        if amount_paid <= 0:
            raise ValidationError('Amount paid must be greater than zero')
        return amount_paid
    
    def clean(self):
        cleaned_data = super().clean()
        payment_date = cleaned_data.get('payment_date')
        
        # Check backdating setting from WorkingMode
        if payment_date:
            from apps.core.models import WorkingMode
            working_mode = WorkingMode.get_active_mode()
            
            # If backdating is not allowed and date is in the past, raise error
            if working_mode and not working_mode.allow_backdating:
                today = timezone.now().date()
                if payment_date < today:
                    raise ValidationError(
                        'Backdating is not allowed. Payment date cannot be earlier than today.'
                    )
        
        return cleaned_data


class GroupRepaymentForm(forms.Form):
    """Form for recording group repayments."""
    
    amount_paid = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter payment amount',
            'required': True
        })
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        initial=timezone.now().date()
    )
    paid_by = forms.ModelChoiceField(
        queryset=Borrower.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        empty_label="Select Group Member"
    )

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group:
            self.fields['paid_by'].queryset = group.members.all()
    
    def clean(self):
        cleaned_data = super().clean()
        payment_date = cleaned_data.get('payment_date')
        
        # Check backdating setting from WorkingMode
        if payment_date:
            from apps.core.models import WorkingMode
            working_mode = WorkingMode.get_active_mode()
            
            # If backdating is not allowed and date is in the past, raise error
            if working_mode and not working_mode.allow_backdating:
                today = timezone.now().date()
                if payment_date < today:
                    raise ValidationError(
                        'Backdating is not allowed. Payment date cannot be earlier than today.'
                    )
        
        return cleaned_data


class LoanApprovalForm(forms.ModelForm):
    """Form for approving loans."""
    
    class Meta:
        model = Loan
        fields = ['amount_approved', 'approval_notes']
        exclude = ['application_date', 'approval_date', 'disbursement_date']
        widgets = {
            'amount_approved': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter approved amount',
                'required': True
            }),
            'approval_notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter approval notes and conditions...'
            }),
        }


class LoanDisbursementForm(forms.ModelForm):
    """Form for disbursing loans."""
    
    class Meta:
        model = LoanDisbursement
        fields = ['amount', 'disbursement_date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter disbursement amount',
                'required': True
            }),
            'disbursement_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Optional disbursement notes...'
            }),
        }

    def __init__(self, *args, loan=None, **kwargs):
        super().__init__(*args, **kwargs)
        if loan:
            self.fields['amount'].initial = loan.amount_approved
            self.fields['disbursement_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        disbursement_date = cleaned_data.get('disbursement_date')
        
        if disbursement_date:
            from apps.core.models import WorkingMode
            working_mode = WorkingMode.get_active_mode()
            
            # If backdating is not allowed and date is in the past, raise error
            if working_mode and not working_mode.allow_backdating:
                today = timezone.now().date()
                if disbursement_date < today:
                    raise ValidationError(
                        'Backdating is not allowed. Disbursement date cannot be earlier than today.'
                    )
        
        return cleaned_data


class PenaltyForm(forms.ModelForm):
    """Form for applying penalties."""
    
    class Meta:
        model = Penalty
        fields = ['amount', 'reason']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter penalty amount',
                'required': True
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Enter reason for penalty...',
                'required': True
            }),
        }


class WrittenOffLoanForm(forms.ModelForm):
    """Form for writing off loans."""
    
    class Meta:
        model = WrittenOffLoan
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Provide detailed reason for writing off this loan...',
                'required': True
            }),
        }


class OldLoanImportForm(forms.ModelForm):
    """Form for importing old loan records."""
    
    class Meta:
        model = OldLoan
        fields = [
            'borrower', 'group', 'amount', 'disbursed_date', 
            'closed_date', 'status', 'notes'
        ]
        widgets = {
            'borrower': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'group': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter loan amount',
                'required': True
            }),
            'disbursed_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'closed_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Optional notes about the old loan...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['borrower'].queryset = Borrower.objects.filter(status='active')
        self.fields['group'].queryset = BorrowerGroup.objects.filter(status='active')
        self.fields['group'].required = False
        self.fields['closed_date'].required = False


class InterestCalculatorForm(forms.Form):
    """Form for testing interest calculations."""
    
    INTEREST_TYPE_CHOICES = [
        ('flat', 'Flat Rate'),
        ('reducing', 'Reducing Balance'),
    ]
    
    principal = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter principal amount',
            'required': True
        })
    )
    interest_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0',
            'max': '100',
            'placeholder': 'Enter annual interest rate %',
            'required': True
        })
    )
    duration_months = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'min': '1',
            'max': '60',
            'placeholder': 'Enter duration in months',
            'required': True
        })
    )
    interest_type = forms.ChoiceField(
        choices=INTEREST_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        })
    )
    repayment_frequency = forms.ChoiceField(
        choices=FrequencyChoices.choices,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        initial=FrequencyChoices.MONTHLY
    )


class RolloverForm(forms.Form):
    """Form for rolling over repayments."""
    
    new_due_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        })
    )
    rollover_fee = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter rollover fee (if any)'
        })
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 2,
            'placeholder': 'Reason for rollover...',
            'required': True
        })
    )

    def clean_new_due_date(self):
        new_due_date = self.cleaned_data.get('new_due_date')
        if new_due_date <= timezone.now().date():
            raise ValidationError('New due date must be in the future')
        return new_due_date


