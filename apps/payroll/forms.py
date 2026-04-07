"""
Forms for the payroll app.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import (
    Department, Position, Employee, PayrollPeriod, AllowanceType, DeductionType,
    EmployeeAllowance, EmployeeDeduction, PayrollRecord, OvertimeRecord,
    BonusRecord, SalaryAdvance
)


class DepartmentForm(forms.ModelForm):
    """Form for creating and editing departments."""
    
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'head_of_department', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'head_of_department': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter head_of_department to show only active employees
        self.fields['head_of_department'].queryset = Employee.objects.filter(status='active')
        self.fields['head_of_department'].empty_label = "Select Head of Department"


class PositionForm(forms.ModelForm):
    """Form for creating and editing positions."""
    
    class Meta:
        model = Position
        fields = ['title', 'department', 'description', 'grade', 'minimum_salary', 'maximum_salary', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'grade': forms.TextInput(attrs={'class': 'form-control'}),
            'minimum_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maximum_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        minimum_salary = cleaned_data.get('minimum_salary')
        maximum_salary = cleaned_data.get('maximum_salary')
        
        if minimum_salary and maximum_salary and minimum_salary > maximum_salary:
            raise ValidationError("Minimum salary cannot be greater than maximum salary.")
        
        return cleaned_data


class EmployeeForm(forms.ModelForm):
    """Form for creating and editing employees."""
    
    class Meta:
        model = Employee
        fields = [
            'first_name', 'middle_name', 'last_name', 'date_of_birth', 'gender',
            'marital_status', 'phone_number', 'email', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'department', 'position', 'employment_type', 'hire_date',
            'basic_salary', 'bank_name', 'bank_account_number', 'bank_branch',
            'tax_id_number', 'nssf_number', 'nhif_number', 'supervisor', 'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'nssf_number': forms.TextInput(attrs={'class': 'form-control'}),
            'nhif_number': forms.TextInput(attrs={'class': 'form-control'}),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['position'].queryset = Position.objects.filter(is_active=True)
        self.fields['supervisor'].queryset = Employee.objects.filter(status='active')
        self.fields['supervisor'].empty_label = "Select Supervisor"
        
        # Make position choices dependent on department
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['position'].queryset = Position.objects.filter(
                    department_id=department_id, is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['position'].queryset = Position.objects.filter(
                department=self.instance.department, is_active=True
            )
    
    def clean_hire_date(self):
        hire_date = self.cleaned_data.get('hire_date')
        if hire_date and hire_date > timezone.now().date():
            raise ValidationError("Hire date cannot be in the future.")
        return hire_date
    
    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            today = timezone.now().date()
            age = (today - date_of_birth).days / 365.25
            if age < 18:
                raise ValidationError("Employee must be at least 18 years old.")
            if age > 65:
                raise ValidationError("Employee cannot be older than 65 years.")
        return date_of_birth
    
    def clean_basic_salary(self):
        basic_salary = self.cleaned_data.get('basic_salary')
        position = self.cleaned_data.get('position')
        
        if basic_salary and position:
            if position.minimum_salary and basic_salary < position.minimum_salary:
                raise ValidationError(
                    f"Basic salary cannot be less than position minimum (Tsh {position.minimum_salary})"
                )
            if position.maximum_salary and basic_salary > position.maximum_salary:
                raise ValidationError(
                    f"Basic salary cannot exceed position maximum (Tsh {position.maximum_salary})"
                )
        
        return basic_salary


class PayrollPeriodForm(forms.ModelForm):
    """Form for creating and editing payroll periods."""
    
    class Meta:
        model = PayrollPeriod
        fields = ['name', 'period_type', 'start_date', 'end_date', 'pay_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'period_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pay_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        pay_date = cleaned_data.get('pay_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("End date must be after start date.")
        
        if pay_date and end_date:
            if pay_date < end_date:
                raise ValidationError("Pay date should be on or after the period end date.")
        
        return cleaned_data


class AllowanceTypeForm(forms.ModelForm):
    """Form for creating and editing allowance types."""
    
    class Meta:
        model = AllowanceType
        fields = ['name', 'code', 'description', 'calculation_type', 'default_amount', 'is_taxable', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'calculation_type': forms.Select(attrs={'class': 'form-control'}),
            'default_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_taxable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DeductionTypeForm(forms.ModelForm):
    """Form for creating and editing deduction types."""
    
    class Meta:
        model = DeductionType
        fields = ['name', 'code', 'description', 'calculation_type', 'default_amount', 'is_statutory', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'calculation_type': forms.Select(attrs={'class': 'form-control'}),
            'default_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_statutory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EmployeeAllowanceForm(forms.ModelForm):
    """Form for managing employee allowances."""
    
    class Meta:
        model = EmployeeAllowance
        fields = ['employee', 'allowance_type', 'amount', 'effective_date', 'end_date', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'allowance_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
        self.fields['allowance_type'].queryset = AllowanceType.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        end_date = cleaned_data.get('end_date')
        
        if effective_date and end_date and effective_date >= end_date:
            raise ValidationError("End date must be after effective date.")
        
        return cleaned_data


class EmployeeDeductionForm(forms.ModelForm):
    """Form for managing employee deductions."""
    
    class Meta:
        model = EmployeeDeduction
        fields = ['employee', 'deduction_type', 'amount', 'effective_date', 'end_date', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'deduction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
        self.fields['deduction_type'].queryset = DeductionType.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        end_date = cleaned_data.get('end_date')
        
        if effective_date and end_date and effective_date >= end_date:
            raise ValidationError("End date must be after effective date.")
        
        return cleaned_data


class OvertimeRecordForm(forms.ModelForm):
    """Form for recording overtime."""
    
    class Meta:
        model = OvertimeRecord
        fields = ['employee', 'date', 'regular_hours', 'overtime_hours', 'overtime_rate', 'hourly_rate', 'description']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'regular_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'overtime_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date > timezone.now().date():
            raise ValidationError("Overtime date cannot be in the future.")
        return date
    
    def clean_overtime_hours(self):
        overtime_hours = self.cleaned_data.get('overtime_hours')
        if overtime_hours and overtime_hours > 12:
            raise ValidationError("Overtime hours cannot exceed 12 hours per day.")
        return overtime_hours


class BonusRecordForm(forms.ModelForm):
    """Form for recording bonuses."""
    
    class Meta:
        model = BonusRecord
        fields = ['employee', 'payroll_period', 'bonus_type', 'amount', 'description']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'payroll_period': forms.Select(attrs={'class': 'form-control'}),
            'bonus_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
        self.fields['payroll_period'].queryset = PayrollPeriod.objects.filter(
            status__in=['draft', 'processing']
        )


class SalaryAdvanceForm(forms.ModelForm):
    """Form for salary advance requests."""
    
    class Meta:
        model = SalaryAdvance
        fields = [
            'employee', 'amount', 'reason', 'monthly_deduction', 
            'number_of_installments', 'repayment_start_date'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'monthly_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'number_of_installments': forms.NumberInput(attrs={'class': 'form-control'}),
            'repayment_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        employee = self.cleaned_data.get('employee')
        
        if amount and employee:
            # Limit advance to 3 months of basic salary
            max_advance = employee.basic_salary * 3
            if amount > max_advance:
                raise ValidationError(
                    f"Advance amount cannot exceed 3 months of basic salary (Tsh {max_advance})"
                )
        
        return amount
    
    def clean_monthly_deduction(self):
        monthly_deduction = self.cleaned_data.get('monthly_deduction')
        employee = self.cleaned_data.get('employee')
        
        if monthly_deduction and employee:
            # Deduction should not exceed 30% of basic salary
            max_deduction = employee.basic_salary * Decimal('0.30')
            if monthly_deduction > max_deduction:
                raise ValidationError(
                    f"Monthly deduction cannot exceed 30% of basic salary (Tsh {max_deduction})"
                )
        
        return monthly_deduction
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        monthly_deduction = cleaned_data.get('monthly_deduction')
        number_of_installments = cleaned_data.get('number_of_installments')
        
        if amount and monthly_deduction and number_of_installments:
            total_repayment = monthly_deduction * number_of_installments
            if total_repayment < amount:
                raise ValidationError(
                    "Total repayment amount is less than advance amount. "
                    "Please adjust monthly deduction or number of installments."
                )
        
        return cleaned_data


class PayrollSearchForm(forms.Form):
    """Form for searching and filtering payroll data."""
    
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status='active'),
        required=False,
        empty_label="All Employees",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payroll_period = forms.ModelChoiceField(
        queryset=PayrollPeriod.objects.all(),
        required=False,
        empty_label="All Periods",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + PayrollRecord.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class BulkPayrollActionForm(forms.Form):
    """Form for bulk payroll actions."""
    
    ACTION_CHOICES = [
        ('calculate', 'Calculate Payroll'),
        ('approve', 'Approve Payroll'),
        ('generate_payslips', 'Generate Payslips'),
        ('mark_paid', 'Mark as Paid'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payroll_records = forms.ModelMultipleChoiceField(
        queryset=PayrollRecord.objects.none(),
        widget=forms.CheckboxSelectMultiple
    )
    
    def __init__(self, *args, **kwargs):
        payroll_period = kwargs.pop('payroll_period', None)
        super().__init__(*args, **kwargs)
        
        if payroll_period:
            self.fields['payroll_records'].queryset = PayrollRecord.objects.filter(
                payroll_period=payroll_period
            )


class PayrollReportForm(forms.Form):
    """Form for generating payroll reports."""
    
    REPORT_TYPE_CHOICES = [
        ('payroll_summary', 'Payroll Summary'),
        ('tax_report', 'Tax Report'),
        ('statutory_report', 'Statutory Deductions Report'),
        ('department_summary', 'Department Summary'),
        ('employee_summary', 'Employee Summary'),
        ('overtime_report', 'Overtime Report'),
        ('bonus_report', 'Bonus Report'),
        ('advance_report', 'Salary Advance Report'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payroll_period = forms.ModelChoiceField(
        queryset=PayrollPeriod.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status='active'),
        required=False,
        empty_label="All Employees",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    format = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV'),
        ],
        initial='pdf',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


