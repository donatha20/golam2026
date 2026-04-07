"""
Forms for financial statements generation and management.
"""
from django import forms
from django.utils import timezone
from datetime import date, timedelta
from .models import (
    AccountingPeriod, FinancialStatementTemplate, AccountClassification,
    BudgetPeriod, BudgetLine
)
from apps.accounting.models import Account


class FinancialStatementGenerationForm(forms.Form):
    """Form for generating financial statements."""
    
    STATEMENT_CHOICES = [
        ('trial_balance', 'Trial Balance'),
        ('balance_sheet', 'Balance Sheet'),
        ('income_statement', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('complete_set', 'Complete Financial Statements'),
    ]
    
    statement_type = forms.ChoiceField(
        choices=STATEMENT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Statement Type'
    )
    
    period = forms.ModelChoiceField(
        queryset=AccountingPeriod.objects.all().order_by('-start_date'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Accounting Period'
    )
    
    comparison_period = forms.ModelChoiceField(
        queryset=AccountingPeriod.objects.all().order_by('-start_date'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Comparison Period (Optional)'
    )
    
    include_zero_balances = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Include Zero Balance Accounts'
    )
    
    export_format = forms.ChoiceField(
        choices=[
            ('html', 'HTML View'),
            ('pdf', 'PDF Export'),
            ('excel', 'Excel Export'),
        ],
        initial='html',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Export Format'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        comparison_period = cleaned_data.get('comparison_period')
        
        if period and comparison_period:
            if period == comparison_period:
                raise forms.ValidationError('Period and comparison period cannot be the same.')
        
        return cleaned_data


class AccountingPeriodForm(forms.ModelForm):
    """Form for creating and editing accounting periods."""
    
    class Meta:
        model = AccountingPeriod
        fields = ['name', 'start_date', 'end_date', 'is_year_end', 'notes']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., January 2024, Q1 2024',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'is_year_end': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about this period...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['name'].label = 'Period Name'
        self.fields['start_date'].label = 'Start Date'
        self.fields['end_date'].label = 'End Date'
        self.fields['is_year_end'].label = 'Year-End Period'
        self.fields['notes'].label = 'Notes'
        
        # Set default dates if creating new period
        if not self.instance.pk:
            today = timezone.now().date()
            # Default to current month
            self.fields['start_date'].initial = today.replace(day=1)
            # Default end date to last day of current month
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            self.fields['end_date'].initial = next_month - timedelta(days=1)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError('End date must be after start date.')
            
            # Check for overlapping periods
            overlapping = AccountingPeriod.objects.filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            
            if overlapping.exists():
                raise forms.ValidationError('This period overlaps with an existing period.')
        
        return cleaned_data


class AccountClassificationForm(forms.ModelForm):
    """Form for classifying accounts for financial statement presentation."""
    
    class Meta:
        model = AccountClassification
        fields = ['account', 'classification_type', 'sort_order', 'is_contra_account', 'notes']
        
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'classification_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'value': '0'
            }),
            'is_contra_account': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about this classification...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['account'].label = 'Account'
        self.fields['classification_type'].label = 'Classification Type'
        self.fields['sort_order'].label = 'Sort Order'
        self.fields['is_contra_account'].label = 'Contra Account'
        self.fields['notes'].label = 'Notes'
        
        # Filter accounts to only active ones
        self.fields['account'].queryset = Account.objects.filter(is_active=True).order_by('account_code')
    
    def clean_account(self):
        account = self.cleaned_data.get('account')
        
        if account:
            # Check if account is already classified (excluding current instance)
            existing = AccountClassification.objects.filter(account=account)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError('This account is already classified.')
        
        return account


class BudgetPeriodForm(forms.ModelForm):
    """Form for creating budget periods."""
    
    class Meta:
        model = BudgetPeriod
        fields = ['name', 'start_date', 'end_date', 'is_active', 'notes']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Budget 2024, Q1 Budget',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about this budget period...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['name'].label = 'Budget Name'
        self.fields['start_date'].label = 'Start Date'
        self.fields['end_date'].label = 'End Date'
        self.fields['is_active'].label = 'Active'
        self.fields['notes'].label = 'Notes'
        
        # Set default active status
        if not self.instance.pk:
            self.fields['is_active'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError('End date must be after start date.')
        
        return cleaned_data


class BudgetLineForm(forms.ModelForm):
    """Form for creating budget line items."""
    
    class Meta:
        model = BudgetLine
        fields = ['budget_period', 'account', 'budgeted_amount', 'notes']
        
        widgets = {
            'budget_period': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'account': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'budgeted_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter budgeted amount',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Optional notes about this budget line...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['budget_period'].label = 'Budget Period'
        self.fields['account'].label = 'Account'
        self.fields['budgeted_amount'].label = 'Budgeted Amount'
        self.fields['notes'].label = 'Notes'
        
        # Filter to active accounts and budget periods
        self.fields['account'].queryset = Account.objects.filter(is_active=True).order_by('account_code')
        self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True).order_by('-start_date')
    
    def clean_budgeted_amount(self):
        amount = self.cleaned_data.get('budgeted_amount')
        if amount and amount < 0:
            raise forms.ValidationError('Budgeted amount cannot be negative.')
        return amount


class PeriodFilterForm(forms.Form):
    """Form for filtering financial statements by period."""
    
    period = forms.ModelChoiceField(
        queryset=AccountingPeriod.objects.all().order_by('-start_date'),
        required=False,
        empty_label="All Periods",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + AccountingPeriod.PERIOD_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Generate year choices from existing periods
        years = AccountingPeriod.objects.dates('start_date', 'year', order='DESC')
        year_choices = [('', 'All Years')] + [(year.year, year.year) for year in years]
        self.fields['year'].choices = year_choices


