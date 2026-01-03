"""
Forms for income and expenditure management.
"""
from django import forms
from django.utils import timezone
from .models import Income, Expenditure, IncomeCategory, ExpenditureCategory, Capital, Shareholder


class IncomeForm(forms.ModelForm):
    """Form for recording income."""
    
    class Meta:
        model = Income
        fields = [
            'source', 'category', 'amount', 'description', 'income_date',
            'reference_number', 'received_from', 'payment_method'
        ]
        
        widgets = {
            'source': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter income amount',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the income source and details...',
                'required': True
            }),
            'income_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Reference/Receipt number (optional)'
            }),
            'received_from': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Source/Person/Organization (optional)'
            }),
            'payment_method': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Cash, Bank Transfer, Cheque, etc.'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['source'].label = 'Income Source'
        self.fields['category'].label = 'Income Category'
        self.fields['amount'].label = 'Amount (₹)'
        self.fields['description'].label = 'Description'
        self.fields['income_date'].label = 'Income Date'
        self.fields['reference_number'].label = 'Reference Number'
        self.fields['received_from'].label = 'Received From'
        self.fields['payment_method'].label = 'Payment Method'
        
        # Set category queryset to active categories only
        self.fields['category'].queryset = IncomeCategory.objects.filter(is_active=True)
        self.fields['category'].empty_label = "Select Category (Optional)"
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['income_date'].initial = timezone.now().date()
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if not description:
            raise forms.ValidationError('Description is required.')
        if len(description) < 10:
            raise forms.ValidationError('Description must be at least 10 characters long.')
        return description


class ExpenditureForm(forms.ModelForm):
    """Form for recording expenditure."""
    
    class Meta:
        model = Expenditure
        fields = [
            'expenditure_type', 'category', 'amount', 'description', 'expenditure_date',
            'vendor_name', 'vendor_contact', 'payment_method', 'reference_number',
            'invoice_number', 'status'
        ]
        
        widgets = {
            'expenditure_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter expenditure amount',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the expenditure purpose and details...',
                'required': True
            }),
            'expenditure_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'vendor_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Vendor/Supplier name',
                'required': True
            }),
            'vendor_contact': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Phone/Email (optional)'
            }),
            'payment_method': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Cash, Bank Transfer, Cheque, etc.'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Payment reference number (optional)'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Invoice/Bill number (optional)'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['expenditure_type'].label = 'Expenditure Type'
        self.fields['category'].label = 'Expenditure Category'
        self.fields['amount'].label = 'Amount (₹)'
        self.fields['description'].label = 'Description'
        self.fields['expenditure_date'].label = 'Expenditure Date'
        self.fields['vendor_name'].label = 'Vendor/Supplier Name'
        self.fields['vendor_contact'].label = 'Vendor Contact'
        self.fields['payment_method'].label = 'Payment Method'
        self.fields['reference_number'].label = 'Reference Number'
        self.fields['invoice_number'].label = 'Invoice Number'
        self.fields['status'].label = 'Approval Status'
        
        # Set category queryset to active categories only
        self.fields['category'].queryset = ExpenditureCategory.objects.filter(is_active=True)
        self.fields['category'].empty_label = "Select Category (Optional)"
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['expenditure_date'].initial = timezone.now().date()
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if not description:
            raise forms.ValidationError('Description is required.')
        if len(description) < 10:
            raise forms.ValidationError('Description must be at least 10 characters long.')
        return description
    
    def clean_vendor_name(self):
        vendor_name = self.cleaned_data.get('vendor_name', '').strip()
        if not vendor_name:
            raise forms.ValidationError('Vendor name is required.')
        return vendor_name


class IncomeCategoryForm(forms.ModelForm):
    """Form for managing income categories."""
    
    class Meta:
        model = IncomeCategory
        fields = ['name', 'description', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter category name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional description of this category...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['name'].label = 'Category Name'
        self.fields['description'].label = 'Description'
        self.fields['is_active'].label = 'Active'
        
        # Set default active status
        if not self.instance.pk:
            self.fields['is_active'].initial = True
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Category name is required.')
        
        # Check for duplicate names (excluding current instance)
        existing = IncomeCategory.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError('A category with this name already exists.')
        
        return name


class ExpenditureCategoryForm(forms.ModelForm):
    """Form for managing expenditure categories."""
    
    class Meta:
        model = ExpenditureCategory
        fields = ['name', 'description', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter category name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional description of this category...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['name'].label = 'Category Name'
        self.fields['description'].label = 'Description'
        self.fields['is_active'].label = 'Active'
        
        # Set default active status
        if not self.instance.pk:
            self.fields['is_active'].initial = True
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Category name is required.')
        
        # Check for duplicate names (excluding current instance)
        existing = ExpenditureCategory.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError('A category with this name already exists.')
        
        return name


class IncomeFilterForm(forms.Form):
    """Form for filtering income records."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by description, ID, or source...'
        })
    )
    
    source = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=IncomeCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set source choices
        source_choices = [('', 'All Sources')] + list(Income.INCOME_SOURCES)
        self.fields['source'].choices = source_choices


class ExpenditureFilterForm(forms.Form):
    """Form for filtering expenditure records."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by description, ID, or vendor...'
        })
    )
    
    expenditure_type = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=ExpenditureCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set expenditure type choices
        type_choices = [('', 'All Types')] + list(Expenditure.EXPENDITURE_TYPES)
        self.fields['expenditure_type'].choices = type_choices
        
        # Set status choices
        status_choices = [('', 'All Statuses')] + list(Expenditure.APPROVAL_STATUS)
        self.fields['status'].choices = status_choices


class ShareholderForm(forms.ModelForm):
    """Form for managing shareholders."""

    class Meta:
        model = Shareholder
        fields = [
            'name', 'shareholder_type', 'email', 'phone_number', 'address',
            'shares_owned', 'share_value', 'join_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter shareholder name'
            }),
            'shareholder_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter address'
            }),
            'shares_owned': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Number of shares'
            }),
            'share_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Value per share'
            }),
            'join_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['join_date'].initial = timezone.now().date()


class CapitalForm(forms.ModelForm):
    """Form for managing capital transactions."""

    class Meta:
        model = Capital
        fields = [
            'capital_type', 'transaction_type', 'amount', 'description',
            'transaction_date', 'shareholder', 'reference_number'
        ]
        widgets = {
            'capital_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter amount'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the capital transaction'
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'shareholder': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Reference number (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transaction_date'].initial = timezone.now().date()
        self.fields['shareholder'].queryset = Shareholder.objects.filter(status='active')
        self.fields['shareholder'].empty_label = "Select Shareholder (optional)"


class CapitalInjectionForm(forms.ModelForm):
    """Form specifically for capital injections."""

    class Meta:
        model = Capital
        fields = [
            'capital_type', 'amount', 'description',
            'transaction_date', 'shareholder', 'reference_number'
        ]
        widgets = {
            'capital_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter amount'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the capital injection'
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'shareholder': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Reference number (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transaction_date'].initial = timezone.now().date()
        self.fields['shareholder'].queryset = Shareholder.objects.filter(status='active')
        self.fields['shareholder'].empty_label = "Select Shareholder (optional)"


class CapitalWithdrawalForm(forms.ModelForm):
    """Form specifically for capital withdrawals."""

    class Meta:
        model = Capital
        fields = [
            'capital_type', 'amount', 'description',
            'transaction_date', 'shareholder', 'reference_number'
        ]
        widgets = {
            'capital_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter amount'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the capital withdrawal'
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'shareholder': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Reference number (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transaction_date'].initial = timezone.now().date()
        self.fields['shareholder'].queryset = Shareholder.objects.filter(status='active')
        self.fields['shareholder'].empty_label = "Select Shareholder (optional)"
