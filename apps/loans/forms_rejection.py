"""
Forms for loan rejection and reversal workflows.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Loan


class LoanRejectionForm(forms.Form):
    """Form for rejecting a loan application."""
    
    rejection_reason = forms.CharField(
        label='Rejection Reason',
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 5,
            'placeholder': 'Provide detailed reason for rejecting this loan application...',
            'required': True
        }),
        help_text='Be specific about why the loan is being rejected'
    )
    
    def clean_rejection_reason(self):
        reason = self.cleaned_data.get('rejection_reason')
        if not reason or not reason.strip():
            raise ValidationError('Rejection reason cannot be empty')
        if len(reason) < 10:
            raise ValidationError('Rejection reason must be at least 10 characters')
        return reason


class LoanRejectionReversalForm(forms.Form):
    """Form for reversing a rejected loan (admin only)."""
    
    reversal_reason = forms.CharField(
        label='Reversal Reason',
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 5,
            'placeholder': 'Explain why the rejection is being reversed...\nExample: New documentation provided, Client circumstances changed, Missing information now received',
            'required': True
        }),
        help_text='Document why this rejection is being reversed'
    )
    
    allow_edits = forms.BooleanField(
        label='Allow Borrower to Edit Loan Details',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        help_text='If checked, loan will return to PENDING status and borrower can edit details'
    )
    
    def clean_reversal_reason(self):
        reason = self.cleaned_data.get('reversal_reason')
        if not reason or not reason.strip():
            raise ValidationError('Reversal reason cannot be empty')
        if len(reason) < 10:
            raise ValidationError('Reversal reason must be at least 10 characters')
        return reason


class RejectedLoanEditForm(forms.ModelForm):
    """Form for editing rejected loans after reversal."""
    
    class Meta:
        model = Loan
        fields = [
            'amount_requested',
            'duration_months',
            'proposed_project',
            'collateral_name',
            'collateral_worth',
            'collateral_withheld',
            'repayment_type',
            'repayment_frequency',
            'pay_method',
            'payment_account',
            'application_notes',
            'notes'
        ]
        widgets = {
            'amount_requested': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '1000',
                'placeholder': 'Enter revised loan amount (TZS)',
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60',
                'placeholder': 'Enter duration in months',
            }),
            'proposed_project': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Brief description of the intended use',
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
            'repayment_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'repayment_frequency': forms.Select(attrs={
                'class': 'form-select',
            }),
            'pay_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'payment_account': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Account number or phone number',
            }),
            'application_notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Any additional notes...',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Internal notes...',
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        collateral_worth = cleaned_data.get('collateral_worth')
        collateral_withheld = cleaned_data.get('collateral_withheld')
        
        if collateral_worth and collateral_withheld:
            if collateral_withheld > collateral_worth:
                raise ValidationError('Amount withheld cannot be greater than collateral worth')
        
        return cleaned_data
