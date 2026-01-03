"""
SMS Management Forms
"""
from django import forms
from django.core.validators import RegexValidator


class SendSMSForm(forms.Form):
    """Form for sending individual SMS."""
    
    phone_number = forms.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?[\d\s\-\(\)]+$',
                message='Enter a valid phone number'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+91 9876543210 or 9876543210',
            'pattern': r'^\+?[\d\s\-\(\)]+$'
        }),
        help_text='Enter phone number with or without country code'
    )
    
    message = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter your SMS message here...',
            'maxlength': 1000
        }),
        help_text='Maximum 1000 characters'
    )
    
    def clean_phone_number(self):
        """Clean and validate phone number."""
        phone = self.cleaned_data['phone_number']
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Remove + if present
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        
        # Validate length
        if len(cleaned) < 10:
            raise forms.ValidationError('Phone number is too short')
        
        if len(cleaned) > 15:
            raise forms.ValidationError('Phone number is too long')
        
        return cleaned
    
    def clean_message(self):
        """Clean and validate message."""
        message = self.cleaned_data['message'].strip()
        
        if not message:
            raise forms.ValidationError('Message cannot be empty')
        
        # Check for minimum length
        if len(message) < 10:
            raise forms.ValidationError('Message is too short (minimum 10 characters)')
        
        return message


class BulkSMSForm(forms.Form):
    """Form for sending bulk SMS."""
    
    RECIPIENT_CHOICES = [
        ('all_borrowers', 'All Borrowers'),
        ('active_borrowers', 'Active Borrowers (with active loans)'),
        ('overdue_borrowers', 'Overdue Borrowers'),
    ]
    
    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='Select the group of recipients'
    )
    
    message = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter your bulk SMS message here...\n\nUse {name} to personalize with borrower name.',
            'maxlength': 1000
        }),
        help_text='Maximum 1000 characters. Use {name} to include borrower name in message.'
    )
    
    confirm_send = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I confirm that I want to send this message to all selected recipients'
    )
    
    def clean_message(self):
        """Clean and validate message."""
        message = self.cleaned_data['message'].strip()
        
        if not message:
            raise forms.ValidationError('Message cannot be empty')
        
        # Check for minimum length
        if len(message) < 10:
            raise forms.ValidationError('Message is too short (minimum 10 characters)')
        
        return message


class SMSTemplateForm(forms.Form):
    """Form for managing SMS templates."""
    
    TEMPLATE_TYPES = [
        ('loan_approval', 'Loan Approval'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('payment_reminder', 'Payment Reminder'),
        ('overdue_reminder', 'Overdue Reminder'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('savings_transaction', 'Savings Transaction'),
        ('custom', 'Custom Template'),
    ]
    
    template_type = forms.ChoiceField(
        choices=TEMPLATE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    template_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter template name'
        })
    )
    
    template_content = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter template content with variables like {{ borrower_name }}, {{ loan_number }}, etc.'
        }),
        help_text='Use Django template variables like {{ borrower_name }}, {{ loan_number }}, {{ amount }}, etc.'
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Active'
    )


class SMSFilterForm(forms.Form):
    """Form for filtering SMS logs."""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('pending', 'Pending'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm'
        })
    )
    
    template_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Template name'
        })
    )
    
    phone_number = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Phone number'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        })
    )
