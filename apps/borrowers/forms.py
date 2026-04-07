"""
Forms for borrower management.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Borrower, BorrowerGroup, GroupMembership, BorrowerDocument
from apps.accounts.models import Branch
from apps.core.models import GenderChoices, MaritalStatusChoices, IDTypeChoices


class BorrowerRegistrationForm(forms.ModelForm):
    """Form for registering new borrowers."""
    
    class Meta:
        model = Borrower
        fields = [
            'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
            'marital_status', 'occupation', 'phone_number', 'email', 'photo',
            'id_type', 'id_number', 'id_issue_date', 'id_expiry_date',
            'house_number', 'street', 'ward', 'district', 'region',
            'next_of_kin_name', 'next_of_kin_relationship', 'next_of_kin_phone',
            'next_of_kin_address', 'branch', 'registration_date', 'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter middle name (optional)'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter occupation'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address (optional)'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'id_type': forms.Select(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ID number'
            }),
            'id_issue_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'id_expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'house_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter house number (optional)'
            }),
            'street': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter street'
            }),
            'ward': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ward'
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter district'
            }),
            'region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter region'
            }),
            'next_of_kin_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter next of kin name'
            }),
            'next_of_kin_relationship': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter relationship'
            }),
            'next_of_kin_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter next of kin phone'
            }),
            'next_of_kin_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter next of kin address'
            }),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'registration_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any additional notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default registration date to today
        self.fields['registration_date'].initial = timezone.now().date()
        
        # Filter branches based on user permissions
        if user:
            if user.is_admin:
                self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
            else:
                # Loan officers can only register to their own branch
                self.fields['branch'].queryset = Branch.objects.filter(
                    id=user.branch.id if user.branch else None
                )
                self.fields['branch'].initial = user.branch
    
    def clean_date_of_birth(self):
        """Validate date of birth."""
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            today = timezone.now().date()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
            
            if age < 18:
                raise ValidationError('Borrower must be at least 18 years old.')
            if age > 100:
                raise ValidationError('Please check the date of birth.')
        
        return date_of_birth
    
    def clean_id_number(self):
        """Validate ID number uniqueness."""
        id_number = self.cleaned_data.get('id_number')
        if id_number:
            # Check if ID number exists for other borrowers (exclude current instance if editing)
            existing = Borrower.objects.filter(id_number=id_number)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('A borrower with this ID number already exists.')
        
        return id_number
    
    def clean_phone_number(self):
        """Validate phone number uniqueness."""
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Check if phone number exists for other borrowers (exclude current instance if editing)
            existing = Borrower.objects.filter(phone_number=phone_number)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('A borrower with this phone number already exists.')
        
        return phone_number


class BorrowerGroupForm(forms.ModelForm):
    """Form for creating borrower groups."""
    
    class Meta:
        model = BorrowerGroup
        fields = [
            'group_name', 'description', 'group_leader', 'formation_date',
            'branch', 'minimum_members', 'maximum_members', 'meeting_frequency',
            'meeting_day', 'notes'
        ]
        widgets = {
            'group_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter group description'
            }),
            'group_leader': forms.Select(attrs={'class': 'form-control'}),
            'formation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'minimum_members': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '3',
                'max': '50'
            }),
            'maximum_members': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'max': '100'
            }),
            'meeting_frequency': forms.Select(attrs={'class': 'form-control'}),
            'meeting_day': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any additional notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default formation date to today
        self.fields['formation_date'].initial = timezone.now().date()
        
        # Filter branches and borrowers based on user permissions
        if user:
            if user.is_admin:
                self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
                self.fields['group_leader'].queryset = Borrower.objects.filter(status='active')
            else:
                # Loan officers can only create groups in their own branch
                self.fields['branch'].queryset = Branch.objects.filter(
                    id=user.branch.id if user.branch else None
                )
                self.fields['branch'].initial = user.branch
                self.fields['group_leader'].queryset = Borrower.objects.filter(
                    status='active',
                    branch=user.branch
                )
    
    def clean_group_name(self):
        """Validate group name uniqueness."""
        group_name = self.cleaned_data.get('group_name')
        if group_name:
            # Check if group name exists for other groups (exclude current instance if editing)
            existing = BorrowerGroup.objects.filter(group_name=group_name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('A group with this name already exists.')
        
        return group_name
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        minimum_members = cleaned_data.get('minimum_members')
        maximum_members = cleaned_data.get('maximum_members')
        
        if minimum_members and maximum_members:
            if minimum_members >= maximum_members:
                raise ValidationError('Maximum members must be greater than minimum members.')
        
        return cleaned_data


class BorrowerDocumentForm(forms.ModelForm):
    """Form for uploading borrower documents."""
    
    class Meta:
        model = BorrowerDocument
        fields = ['document_type', 'document_name', 'document_file', 'description']
        widgets = {
            'document_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter document type'
            }),
            'document_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter document name'
            }),
            'document_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter document description (optional)'
            }),
        }


class BorrowerSearchForm(forms.Form):
    """Form for searching borrowers."""
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, ID, or phone...',
            'autocomplete': 'off'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(Borrower._meta.get_field('status').choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    gender = forms.ChoiceField(
        choices=[('', 'All Genders')] + list(GenderChoices.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        required=False,
        empty_label="All Branches",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


