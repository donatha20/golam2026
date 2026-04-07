"""
Forms for asset and collateral management.
"""
from django import forms
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from decimal import Decimal

from .models import (
    Asset, AssetCategory, AssetDocument, AssetValuation,
    Collateral, CollateralType, CollateralDocument, CollateralValuation
)
from apps.accounts.models import CustomUser
from apps.borrowers.models import Borrower
from apps.loans.models import Loan


class AssetForm(forms.ModelForm):
    """Form for creating and editing assets."""
    
    class Meta:
        model = Asset
        fields = [
            'asset_name', 'category', 'description', 'purchase_date', 'purchase_value',
            'current_value', 'salvage_value', 'depreciation_method', 'custom_depreciation_rate',
            'serial_number', 'model_number', 'manufacturer', 'condition', 'location',
            'department', 'assigned_to', 'status', 'warranty_expiry', 'supplier',
            'purchase_order_number', 'insurance_policy_number', 'insurance_expiry', 'notes'
        ]
        
        widgets = {
            'asset_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter asset name',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter asset description...'
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'purchase_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter purchase value',
                'required': True
            }),
            'current_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter current value',
                'required': True
            }),
            'salvage_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter salvage value'
            }),
            'depreciation_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'custom_depreciation_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'max': '100.00',
                'placeholder': 'Override category rate if needed'
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter serial number'
            }),
            'model_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter model number'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter manufacturer'
            }),
            'condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter asset location'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter department'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'warranty_expiry': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter supplier name'
            }),
            'purchase_order_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter PO number'
            }),
            'insurance_policy_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter insurance policy number'
            }),
            'insurance_expiry': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter additional notes...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['asset_name'].label = 'Asset Name'
        self.fields['category'].label = 'Category'
        self.fields['description'].label = 'Description'
        self.fields['purchase_date'].label = 'Purchase Date'
        self.fields['purchase_value'].label = 'Purchase Value (Tsh)'
        self.fields['current_value'].label = 'Current Value (Tsh)'
        self.fields['salvage_value'].label = 'Salvage Value (Tsh)'
        self.fields['depreciation_method'].label = 'Depreciation Method'
        self.fields['custom_depreciation_rate'].label = 'Custom Depreciation Rate (%)'
        self.fields['serial_number'].label = 'Serial Number'
        self.fields['model_number'].label = 'Model Number'
        self.fields['manufacturer'].label = 'Manufacturer'
        self.fields['condition'].label = 'Condition'
        self.fields['location'].label = 'Location'
        self.fields['department'].label = 'Department'
        self.fields['assigned_to'].label = 'Assigned To'
        self.fields['status'].label = 'Status'
        self.fields['warranty_expiry'].label = 'Warranty Expiry'
        self.fields['supplier'].label = 'Supplier'
        self.fields['purchase_order_number'].label = 'Purchase Order Number'
        self.fields['insurance_policy_number'].label = 'Insurance Policy Number'
        self.fields['insurance_expiry'].label = 'Insurance Expiry'
        self.fields['notes'].label = 'Notes'
        
        # Set default values
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.now().date()
            self.fields['status'].initial = 'active'
            self.fields['condition'].initial = 'good'
            self.fields['depreciation_method'].initial = 'straight_line'
        
        # Filter querysets
        self.fields['category'].queryset = AssetCategory.objects.filter(is_active=True)
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
        self.fields['assigned_to'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        purchase_value = cleaned_data.get('purchase_value')
        current_value = cleaned_data.get('current_value')
        salvage_value = cleaned_data.get('salvage_value')
        
        if purchase_value and current_value and current_value > purchase_value:
            raise forms.ValidationError('Current value cannot exceed purchase value.')
        
        if purchase_value and salvage_value and salvage_value >= purchase_value:
            raise forms.ValidationError('Salvage value must be less than purchase value.')
        
        return cleaned_data


class CollateralForm(forms.ModelForm):
    """Form for creating and editing collaterals."""
    
    class Meta:
        model = Collateral
        fields = [
            'borrower', 'loan', 'collateral_type', 'title', 'description',
            'brand_model', 'serial_number', 'year_of_manufacture', 'condition',
            'estimated_value', 'market_value', 'forced_sale_value', 'valuation_method',
            'valuated_by', 'location', 'ownership_status', 'owner_name', 'owner_relationship',
            'registration_number', 'registration_authority', 'legal_title_holder',
            'encumbrance_details', 'is_insured', 'insurance_company', 'insurance_policy_number',
            'insurance_value', 'insurance_expiry', 'special_conditions', 'notes'
        ]
        
        widgets = {
            'borrower': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'loan': forms.Select(attrs={
                'class': 'form-select'
            }),
            'collateral_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter collateral title',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter detailed description...',
                'required': True
            }),
            'brand_model': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter brand/model'
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter serial number'
            }),
            'year_of_manufacture': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1900',
                'max': timezone.now().year,
                'placeholder': 'Enter year'
            }),
            'condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estimated_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter estimated value',
                'required': True
            }),
            'market_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter market value'
            }),
            'forced_sale_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter forced sale value'
            }),
            'valuation_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'valuated_by': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter valuator name'
            }),
            'location': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Enter collateral location...',
                'required': True
            }),
            'ownership_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter owner name if different from borrower'
            }),
            'owner_relationship': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter relationship to borrower'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter registration number'
            }),
            'registration_authority': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter registration authority'
            }),
            'legal_title_holder': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter legal title holder'
            }),
            'encumbrance_details': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter details of existing loans, mortgages, or liens...'
            }),
            'is_insured': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'insurance_company': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter insurance company'
            }),
            'insurance_policy_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter policy number'
            }),
            'insurance_value': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.00',
                'placeholder': 'Enter insurance value'
            }),
            'insurance_expiry': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'special_conditions': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter any special conditions...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter additional notes...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['borrower'].label = 'Borrower'
        self.fields['loan'].label = 'Loan (Optional)'
        self.fields['collateral_type'].label = 'Collateral Type'
        self.fields['title'].label = 'Title'
        self.fields['description'].label = 'Description'
        self.fields['brand_model'].label = 'Brand/Model'
        self.fields['serial_number'].label = 'Serial Number'
        self.fields['year_of_manufacture'].label = 'Year of Manufacture'
        self.fields['condition'].label = 'Condition'
        self.fields['estimated_value'].label = 'Estimated Value (Tsh)'
        self.fields['market_value'].label = 'Market Value (Tsh)'
        self.fields['forced_sale_value'].label = 'Forced Sale Value (Tsh)'
        self.fields['valuation_method'].label = 'Valuation Method'
        self.fields['valuated_by'].label = 'Valuated By'
        self.fields['location'].label = 'Location'
        self.fields['ownership_status'].label = 'Ownership Status'
        self.fields['owner_name'].label = 'Owner Name'
        self.fields['owner_relationship'].label = 'Owner Relationship'
        self.fields['registration_number'].label = 'Registration Number'
        self.fields['registration_authority'].label = 'Registration Authority'
        self.fields['legal_title_holder'].label = 'Legal Title Holder'
        self.fields['encumbrance_details'].label = 'Encumbrance Details'
        self.fields['is_insured'].label = 'Is Insured'
        self.fields['insurance_company'].label = 'Insurance Company'
        self.fields['insurance_policy_number'].label = 'Insurance Policy Number'
        self.fields['insurance_value'].label = 'Insurance Value (Tsh)'
        self.fields['insurance_expiry'].label = 'Insurance Expiry'
        self.fields['special_conditions'].label = 'Special Conditions'
        self.fields['notes'].label = 'Notes'
        
        # Set default values
        if not self.instance.pk:
            self.fields['condition'].initial = 'good'
            self.fields['ownership_status'].initial = 'owned'
            self.fields['valuation_method'].initial = 'self_declared'
        
        # Filter querysets
        self.fields['borrower'].queryset = Borrower.objects.filter(status='active').order_by('first_name', 'last_name')
        self.fields['loan'].queryset = Loan.objects.filter(status__in=['approved', 'disbursed']).order_by('-created_at')
        self.fields['collateral_type'].queryset = CollateralType.objects.filter(is_active=True)
        self.fields['loan'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        estimated_value = cleaned_data.get('estimated_value')
        market_value = cleaned_data.get('market_value')
        forced_sale_value = cleaned_data.get('forced_sale_value')
        
        if market_value and estimated_value and market_value > estimated_value * Decimal('1.5'):
            raise forms.ValidationError('Market value seems unusually high compared to estimated value.')
        
        if forced_sale_value and estimated_value and forced_sale_value > estimated_value:
            raise forms.ValidationError('Forced sale value cannot exceed estimated value.')
        
        return cleaned_data


class AssetDocumentForm(forms.ModelForm):
    """Form for uploading asset documents."""

    class Meta:
        model = AssetDocument
        fields = ['document_type', 'title', 'description', 'document_file']

        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter document title',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter document description...'
            }),
            'document_file': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set field labels
        self.fields['document_type'].label = 'Document Type'
        self.fields['title'].label = 'Title'
        self.fields['description'].label = 'Description'
        self.fields['document_file'].label = 'Document File'

    def clean_document_file(self):
        document_file = self.cleaned_data.get('document_file')

        if document_file:
            # Check file size (max 10MB)
            if document_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')

            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_extension = document_file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError('File type not allowed. Please upload PDF, Word, or image files.')

        return document_file


class CollateralDocumentForm(forms.ModelForm):
    """Form for uploading collateral documents."""

    class Meta:
        model = CollateralDocument
        fields = ['document_type', 'title', 'description', 'document_file']

        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter document title',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Enter document description...'
            }),
            'document_file': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set field labels
        self.fields['document_type'].label = 'Document Type'
        self.fields['title'].label = 'Title'
        self.fields['description'].label = 'Description'
        self.fields['document_file'].label = 'Document File'

    def clean_document_file(self):
        document_file = self.cleaned_data.get('document_file')

        if document_file:
            # Check file size (max 10MB)
            if document_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')

            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_extension = document_file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError('File type not allowed. Please upload PDF, Word, or image files.')

        return document_file


