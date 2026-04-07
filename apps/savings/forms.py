"""
Forms for savings management system.
"""
from django import forms
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from .models import (
    SavingsProduct, SavingsLoanRule, SavingsAccount, SavingsTransaction,
    SavingsInterestCalculation, SavingsAccountHold
)
from apps.accounts.models import CustomUser
from apps.borrowers.models import Borrower


class SavingsAccountForm(forms.ModelForm):
    """Form for opening new savings accounts."""
    
    class Meta:
        model = SavingsAccount
        fields = [
            'borrower', 'savings_product', 'opened_date', 'notes'
        ]
        
        widgets = {
            'borrower': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'savings_product': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'opened_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter any notes about the account...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['borrower'].label = 'Borrower'
        self.fields['savings_product'].label = 'Savings Product'
        self.fields['opened_date'].label = 'Opening Date'
        self.fields['notes'].label = 'Notes'
        
        # Set default values
        if not self.instance.pk:
            self.fields['opened_date'].initial = timezone.now().date()
        
        # Filter querysets
        self.fields['borrower'].queryset = Borrower.objects.filter(status='active').order_by('first_name', 'last_name')
        self.fields['savings_product'].queryset = SavingsProduct.objects.filter(is_active=True)
    
    def clean_borrower(self):
        borrower = self.cleaned_data.get('borrower')
        
        # Check if borrower already has an account with the same product
        if borrower and self.cleaned_data.get('savings_product'):
            existing_account = SavingsAccount.objects.filter(
                borrower=borrower,
                savings_product=self.cleaned_data['savings_product'],
                status__in=['active', 'dormant']
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_account.exists():
                raise forms.ValidationError(
                    f'Borrower already has an active account with this product.'
                )
        
        return borrower


class SavingsTransactionForm(forms.ModelForm):
    """Form for processing savings transactions."""
    
    initial_deposit = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Enter initial deposit amount'
        }),
        label='Initial Deposit (for new accounts)',
        help_text='Required for new account opening'
    )
    
    class Meta:
        model = SavingsTransaction
        fields = [
            'savings_account', 'transaction_type', 'amount', 'description',
            'transaction_date', 'reference_number'
        ]
        
        widgets = {
            'savings_account': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter transaction amount',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter transaction description...',
                'required': True
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter reference number (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['savings_account'].label = 'Savings Account'
        self.fields['transaction_type'].label = 'Transaction Type'
        self.fields['amount'].label = 'Amount (Tsh)'
        self.fields['description'].label = 'Description'
        self.fields['transaction_date'].label = 'Transaction Date'
        self.fields['reference_number'].label = 'Reference Number'
        
        # Set default values
        if not self.instance.pk:
            self.fields['transaction_date'].initial = timezone.now().date()
        
        # Filter active accounts
        self.fields['savings_account'].queryset = SavingsAccount.objects.filter(
            status='active'
        ).select_related('borrower').order_by('account_number')
    
    def clean(self):
        cleaned_data = super().clean()
        savings_account = cleaned_data.get('savings_account')
        transaction_type = cleaned_data.get('transaction_type')
        amount = cleaned_data.get('amount')
        
        if savings_account and transaction_type and amount:
            if transaction_type == 'deposit':
                can_deposit, message = savings_account.can_deposit(amount)
                if not can_deposit:
                    raise forms.ValidationError(f'Deposit not allowed: {message}')
            
            elif transaction_type == 'withdrawal':
                can_withdraw, message = savings_account.can_withdraw(amount)
                if not can_withdraw:
                    raise forms.ValidationError(f'Withdrawal not allowed: {message}')
        
        return cleaned_data


class SavingsProductForm(forms.ModelForm):
    """Form for creating and editing savings products."""
    
    class Meta:
        model = SavingsProduct
        fields = [
            'name', 'description', 'interest_rate', 'interest_calculation_method',
            'interest_posting_frequency', 'minimum_opening_balance', 'minimum_balance',
            'maximum_balance', 'minimum_deposit', 'maximum_deposit_per_day',
            'minimum_withdrawal', 'maximum_withdrawal_per_day', 'account_maintenance_fee',
            'withdrawal_fee', 'is_active', 'requires_approval', 'allow_overdraft'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter product name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter product description...'
            }),
            'interest_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'max': '50.00',
                'placeholder': 'Enter annual interest rate',
                'required': True
            }),
            'interest_calculation_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'interest_posting_frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'minimum_opening_balance': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter minimum opening balance',
                'required': True
            }),
            'minimum_balance': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter minimum balance',
                'required': True
            }),
            'maximum_balance': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter maximum balance (optional)'
            }),
            'minimum_deposit': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter minimum deposit amount',
                'required': True
            }),
            'maximum_deposit_per_day': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter daily deposit limit (optional)'
            }),
            'minimum_withdrawal': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter minimum withdrawal amount',
                'required': True
            }),
            'maximum_withdrawal_per_day': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter daily withdrawal limit (optional)'
            }),
            'account_maintenance_fee': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter monthly maintenance fee'
            }),
            'withdrawal_fee': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter withdrawal fee'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'allow_overdraft': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['name'].label = 'Product Name'
        self.fields['description'].label = 'Description'
        self.fields['interest_rate'].label = 'Interest Rate (%)'
        self.fields['interest_calculation_method'].label = 'Interest Calculation Method'
        self.fields['interest_posting_frequency'].label = 'Interest Posting Frequency'
        self.fields['minimum_opening_balance'].label = 'Minimum Opening Balance (Tsh)'
        self.fields['minimum_balance'].label = 'Minimum Balance (Tsh)'
        self.fields['maximum_balance'].label = 'Maximum Balance (Tsh)'
        self.fields['minimum_deposit'].label = 'Minimum Deposit (Tsh)'
        self.fields['maximum_deposit_per_day'].label = 'Daily Deposit Limit (Tsh)'
        self.fields['minimum_withdrawal'].label = 'Minimum Withdrawal (Tsh)'
        self.fields['maximum_withdrawal_per_day'].label = 'Daily Withdrawal Limit (Tsh)'
        self.fields['account_maintenance_fee'].label = 'Monthly Maintenance Fee (Tsh)'
        self.fields['withdrawal_fee'].label = 'Withdrawal Fee (Tsh)'
        self.fields['is_active'].label = 'Is Active'
        self.fields['requires_approval'].label = 'Requires Approval'
        self.fields['allow_overdraft'].label = 'Allow Overdraft'
    
    def clean(self):
        cleaned_data = super().clean()
        minimum_balance = cleaned_data.get('minimum_balance')
        minimum_opening_balance = cleaned_data.get('minimum_opening_balance')
        maximum_balance = cleaned_data.get('maximum_balance')
        
        if minimum_opening_balance and minimum_balance:
            if minimum_opening_balance < minimum_balance:
                raise forms.ValidationError(
                    'Minimum opening balance cannot be less than minimum balance.'
                )
        
        if maximum_balance and minimum_balance:
            if maximum_balance <= minimum_balance:
                raise forms.ValidationError(
                    'Maximum balance must be greater than minimum balance.'
                )
        
        return cleaned_data


class SavingsLoanRuleForm(forms.ModelForm):
    """Form for creating and editing savings loan rules."""

    class Meta:
        model = SavingsLoanRule
        fields = [
            'name', 'description', 'rule_type', 'loan_type', 'minimum_balance_required',
            'minimum_savings_period_months', 'savings_to_loan_ratio', 'mandatory_savings_amount',
            'is_active', 'is_mandatory', 'grace_period_days'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter rule name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter rule description...'
            }),
            'rule_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'loan_type': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter loan type (e.g., personal, business)',
                'required': True
            }),
            'minimum_balance_required': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter minimum balance required'
            }),
            'minimum_savings_period_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'placeholder': 'Enter minimum months of savings'
            }),
            'savings_to_loan_ratio': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'max': '100.00',
                'placeholder': 'Enter savings percentage of loan amount'
            }),
            'mandatory_savings_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter mandatory savings amount'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'is_mandatory': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'grace_period_days': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'placeholder': 'Enter grace period in days'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set field labels
        self.fields['name'].label = 'Rule Name'
        self.fields['description'].label = 'Description'
        self.fields['rule_type'].label = 'Rule Type'
        self.fields['loan_type'].label = 'Loan Type'
        self.fields['minimum_balance_required'].label = 'Minimum Balance Required (Tsh)'
        self.fields['minimum_savings_period_months'].label = 'Minimum Savings Period (Months)'
        self.fields['savings_to_loan_ratio'].label = 'Savings to Loan Ratio (%)'
        self.fields['mandatory_savings_amount'].label = 'Mandatory Savings Amount (Tsh)'
        self.fields['is_active'].label = 'Is Active'
        self.fields['is_mandatory'].label = 'Is Mandatory'
        self.fields['grace_period_days'].label = 'Grace Period (Days)'

    def clean(self):
        cleaned_data = super().clean()
        rule_type = cleaned_data.get('rule_type')

        # Validate rule-specific fields
        if rule_type == 'minimum_balance' and not cleaned_data.get('minimum_balance_required'):
            raise forms.ValidationError('Minimum balance required is mandatory for this rule type.')

        if rule_type == 'savings_period' and not cleaned_data.get('minimum_savings_period_months'):
            raise forms.ValidationError('Minimum savings period is mandatory for this rule type.')

        if rule_type == 'savings_ratio' and not cleaned_data.get('savings_to_loan_ratio'):
            raise forms.ValidationError('Savings to loan ratio is mandatory for this rule type.')

        if rule_type == 'mandatory_savings' and not cleaned_data.get('mandatory_savings_amount'):
            raise forms.ValidationError('Mandatory savings amount is mandatory for this rule type.')

        return cleaned_data


class InterestCalculationForm(forms.Form):
    """Form for calculating interest on savings accounts."""

    calculation_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        label='Calculation Date',
        initial=timezone.now().date()
    )

    period_start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        label='Period Start Date'
    )

    period_end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'required': True
        }),
        label='Period End Date'
    )

    accounts = forms.ModelMultipleChoiceField(
        queryset=SavingsAccount.objects.filter(status='active', balance__gt=0),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox-list'
        }),
        label='Select Accounts',
        required=False,
        help_text='Leave empty to calculate for all eligible accounts'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default period (last month)
        today = timezone.now().date()
        first_day_last_month = today.replace(day=1) - timedelta(days=1)
        first_day_last_month = first_day_last_month.replace(day=1)
        last_day_last_month = today.replace(day=1) - timedelta(days=1)

        self.fields['period_start_date'].initial = first_day_last_month
        self.fields['period_end_date'].initial = last_day_last_month

    def clean(self):
        cleaned_data = super().clean()
        period_start_date = cleaned_data.get('period_start_date')
        period_end_date = cleaned_data.get('period_end_date')
        calculation_date = cleaned_data.get('calculation_date')

        if period_start_date and period_end_date:
            if period_end_date <= period_start_date:
                raise forms.ValidationError('Period end date must be after start date.')

        if calculation_date and period_end_date:
            if calculation_date < period_end_date:
                raise forms.ValidationError('Calculation date cannot be before period end date.')

        return cleaned_data


