"""
Clean, simplified forms for income and expenditure management.
"""
from django import forms
from django.utils import timezone
from apps.core.models import IncomeSource, ExpenseCategory
from .models import Income, Expenditure, IncomeCategory, ExpenditureCategory, Capital, Shareholder


class IncomeForm(forms.ModelForm):
    """Form for recording income with configured sources."""
    
    class Meta:
        model = Income
        # Expose only the transaction fields required by the simplified UI
        fields = [
            'source', 'amount', 'description', 'income_date'
        ]
        widgets = {
            'source': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 3,
                'placeholder': 'Describe the income...'
            }),
            'income_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            # Note: other Income model fields (reference_number, received_from, payment_method)
            # are intentionally excluded from the form to simplify the transaction UI.
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load active income sources from configured IncomeSource objects
        from apps.core.models import IncomeSource
        configured_sources = IncomeSource.objects.filter(is_active=True).order_by('name')

        # If there are configured sources, use them as queryset for the FK field
        if configured_sources.exists():
            self.fields['source'].queryset = configured_sources
            self.fields['source'].empty_label = '--- Select Income Source ---'
        else:
            # Fallback to legacy static choices when no configured sources exist
            self.fields['source'].choices = [('', '--- Select Income Source ---')] + list(Income.INCOME_SOURCES)

        # Set labels
        # Display the Income Source as "Income Name" in the simplified form
        self.fields['source'].label = 'Income Name'
        self.fields['amount'].label = 'Amount (Tsh)'
        self.fields['income_date'].label = 'Date'
        self.fields['description'].label = 'Description'
        

        # Set default date
        if not self.instance.pk:
            self.fields['income_date'].initial = timezone.now().date()


class ExpenditureForm(forms.ModelForm):
    """Form for recording expenditure with configured expense categories."""
    
    class Meta:
        model = Expenditure
        # Only show the simplified transaction fields; vendor_name is required by the model
        # so we include it as a hidden field and default it when not supplied.
        fields = [
            'expenditure_type', 'amount', 'description', 'expenditure_date', 'vendor_name'
        ]
        widgets = {
            'expenditure_type': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 3,
                'placeholder': 'Describe the expenditure...'
            }),
            'expenditure_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            # vendor_name is included as a hidden input in the simplified UI, but we provide
            # a widget here in case the form is rendered as a ModelForm in edit views.
            'vendor_name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Vendor or supplier name'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load active expense categories from configured ExpenseCategory objects
        from apps.core.models import ExpenseCategory
        configured_types = ExpenseCategory.objects.filter(is_active=True).order_by('name')

        if configured_types.exists():
            self.fields['expenditure_type'].queryset = configured_types
            self.fields['expenditure_type'].empty_label = '--- Select Expense Type ---'
        else:
            # Fallback to legacy static choices when no configured types exist
            self.fields['expenditure_type'].choices = [('', '--- Select Expense Type ---')] + list(Expenditure.EXPENDITURE_TYPES)

        # Set labels
        # Display Expenditure type as "Expenditure Name" in the simplified form
        self.fields['expenditure_type'].label = 'Expenditure Name'
        self.fields['amount'].label = 'Amount (Tsh)'
        self.fields['expenditure_date'].label = 'Date'
        self.fields['description'].label = 'Description'
        self.fields['vendor_name'].label = 'Vendor/Supplier (hidden)'

        # Set default date
        if not self.instance.pk:
            self.fields['expenditure_date'].initial = timezone.now().date()

        # Ensure a vendor_name exists for the model (model requires vendor_name non-null)
        if not self.initial.get('vendor_name') and not getattr(self.instance, 'vendor_name', None):
            self.initial['vendor_name'] = 'Unknown'

    def clean(self):
        cleaned = super().clean()
        # Provide a default vendor name if none supplied (form hides vendor field from users)
        if not cleaned.get('vendor_name'):
            cleaned['vendor_name'] = 'Unknown'
        return cleaned
class IncomeCategoryForm(forms.ModelForm):
    """Form for managing income categories."""
    
    class Meta:
        model = IncomeCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Name'
        self.fields['description'].label = 'Description'
        self.fields['is_active'].label = 'Active'
        
        if not self.instance.pk:
            self.fields['is_active'].initial = True


class ExpenditureCategoryForm(forms.ModelForm):
    """Form for managing expenditure categories."""
    
    class Meta:
        model = ExpenditureCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Name'
        self.fields['description'].label = 'Description'
        self.fields['is_active'].label = 'Active'
        
        if not self.instance.pk:
            self.fields['is_active'].initial = True


# ============= FILTER FORMS =============

class IncomeFilterForm(forms.Form):
    """Form for filtering income records."""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Search by ID or description...'
        })
    )
    from apps.core.models import IncomeSource
    source = forms.ModelChoiceField(
        required=False,
        queryset=IncomeSource.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    status = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Use configured IncomeSource queryset; set an empty label for the model choice field
        try:
            self.fields['source'].empty_label = '--- All Sources ---'
        except Exception:
            # If field isn't a ModelChoiceField (fallback), leave choices as legacy
            self.fields['source'].choices = [('', '--- All Sources ---')] + list(Income.INCOME_SOURCES)
        
        # Set status choices
        self.fields['status'].choices = [('', '--- All Statuses ---')] + list(Income.STATUS_CHOICES)


class ExpenditureFilterForm(forms.Form):
    """Form for filtering expenditure records."""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Search by ID or description...'
        })
    )
    from apps.core.models import ExpenseCategory
    type = forms.ModelChoiceField(
        required=False,
        queryset=ExpenseCategory.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Expenditure Type'
    )
    status = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Use configured ExpenseCategory queryset; set an empty label for the model choice field
        try:
            self.fields['type'].empty_label = '--- All Types ---'
        except Exception:
            self.fields['type'].choices = [('', '--- All Types ---')] + list(Expenditure.EXPENDITURE_TYPES)
        
        # Set status choices
        self.fields['status'].choices = [('', '--- All Statuses ---')] + list(Expenditure.STATUS_CHOICES)


# ============= OTHER FORMS =============

class ShareholderForm(forms.ModelForm):
    """Form for managing shareholders."""
    
    class Meta:
        model = Shareholder
        fields = ['name', 'shareholder_type', 'email', 'phone_number', 'address', 'shares_owned', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'shareholder_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'shares_owned': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '1'}),
            'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }


class CapitalForm(forms.ModelForm):
    """Form for managing capital."""
    
    class Meta:
        model = Capital
        fields = ['capital_type', 'transaction_type', 'amount', 'description', 'shareholder', 'transaction_date']
        widgets = {
            'capital_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'shareholder': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'transaction_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }


class CapitalInjectionForm(forms.ModelForm):
    """Form for capital injection."""
    
    class Meta:
        model = Capital
        fields = ['capital_type', 'amount', 'description', 'shareholder', 'transaction_date']
        widgets = {
            'capital_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'shareholder': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'transaction_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['transaction_date'].initial = timezone.now().date()


class CapitalWithdrawalForm(forms.ModelForm):
    """Form for capital withdrawal."""
    
    class Meta:
        model = Capital
        fields = ['capital_type', 'amount', 'description', 'shareholder', 'transaction_date']
        widgets = {
            'capital_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'shareholder': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'transaction_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['transaction_date'].initial = timezone.now().date()
