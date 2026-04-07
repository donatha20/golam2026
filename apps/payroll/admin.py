"""
Admin configuration for the payroll app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Department, Position, Employee, PayrollPeriod, AllowanceType, DeductionType,
    EmployeeAllowance, EmployeeDeduction, PayrollRecord, OvertimeRecord,
    BonusRecord, SalaryAdvance, Payslip, PayrollReport, PayrollAllowance,
    PayrollDeduction, AdvanceDeduction
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'head_of_department', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('head_of_department')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'grade', 'minimum_salary', 'maximum_salary', 'is_active']
    list_filter = ['department', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'grade']
    ordering = ['department', 'title']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department')


class EmployeeAllowanceInline(admin.TabularInline):
    model = EmployeeAllowance
    extra = 0
    fields = ['allowance_type', 'amount', 'effective_date', 'end_date', 'is_active']


class EmployeeDeductionInline(admin.TabularInline):
    model = EmployeeDeduction
    extra = 0
    fields = ['deduction_type', 'amount', 'effective_date', 'end_date', 'is_active']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_id', 'get_full_name', 'department', 'position', 
        'employment_type', 'status', 'basic_salary', 'hire_date'
    ]
    list_filter = [
        'status', 'department', 'employment_type', 'gender', 
        'marital_status', 'hire_date'
    ]
    search_fields = [
        'employee_id', 'first_name', 'last_name', 'email', 
        'phone_number', 'tax_id_number'
    ]
    ordering = ['employee_id']
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'employee_id', 'user', 'first_name', 'middle_name', 'last_name',
                'date_of_birth', 'gender', 'marital_status', 'profile_photo'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone_number', 'email', 'address',
                'emergency_contact_name', 'emergency_contact_phone'
            )
        }),
        ('Employment Details', {
            'fields': (
                'department', 'position', 'employment_type', 'hire_date',
                'termination_date', 'status', 'supervisor'
            )
        }),
        ('Salary Information', {
            'fields': ('basic_salary', 'currency')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account_number', 'bank_branch')
        }),
        ('Statutory Information', {
            'fields': ('tax_id_number', 'nssf_number', 'nhif_number')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        })
    )
    
    readonly_fields = ['employee_id']
    inlines = [EmployeeAllowanceInline, EmployeeDeductionInline]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'department', 'position', 'supervisor'
        )


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'period_type', 'start_date', 'end_date', 'pay_date',
        'status', 'total_employees', 'total_net_salary', 'is_approved'
    ]
    list_filter = ['period_type', 'status', 'is_processed', 'is_approved']
    search_fields = ['name']
    ordering = ['-start_date']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('name', 'period_type', 'start_date', 'end_date', 'pay_date')
        }),
        ('Processing Status', {
            'fields': (
                'status', 'is_processed', 'processed_date', 'processed_by',
                'is_approved', 'approved_by', 'approval_date'
            )
        }),
        ('Summary', {
            'fields': (
                'total_employees', 'total_gross_salary', 
                'total_deductions', 'total_net_salary'
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )
    
    readonly_fields = [
        'total_employees', 'total_gross_salary', 'total_deductions', 
        'total_net_salary', 'processed_date', 'processed_by',
        'approval_date', 'approved_by'
    ]
    
    actions = ['process_payroll']
    
    def process_payroll(self, request, queryset):
        for period in queryset:
            if period.can_be_processed():
                period.process_payroll(request.user)
                self.message_user(request, f"Payroll processed for {period.name}")
            else:
                self.message_user(
                    request, 
                    f"Cannot process payroll for {period.name} - check status",
                    level='warning'
                )
    process_payroll.short_description = "Process selected payroll periods"


@admin.register(AllowanceType)
class AllowanceTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'calculation_type', 'default_amount', 'is_taxable', 'is_active']
    list_filter = ['calculation_type', 'is_taxable', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['name']


@admin.register(DeductionType)
class DeductionTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'calculation_type', 'default_amount', 'is_statutory', 'is_active']
    list_filter = ['calculation_type', 'is_statutory', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['name']


@admin.register(EmployeeAllowance)
class EmployeeAllowanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'allowance_type', 'amount', 'effective_date', 'end_date', 'is_active']
    list_filter = ['allowance_type', 'is_active', 'effective_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'allowance_type__name']
    ordering = ['employee', 'allowance_type']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'allowance_type')


@admin.register(EmployeeDeduction)
class EmployeeDeductionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'deduction_type', 'amount', 'effective_date', 'end_date', 'is_active']
    list_filter = ['deduction_type', 'is_active', 'effective_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'deduction_type__name']
    ordering = ['employee', 'deduction_type']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'deduction_type')


class PayrollAllowanceInline(admin.TabularInline):
    model = PayrollAllowance
    extra = 0
    readonly_fields = ['allowance_type', 'base_amount', 'amount']


class PayrollDeductionInline(admin.TabularInline):
    model = PayrollDeduction
    extra = 0
    readonly_fields = ['deduction_type', 'base_amount', 'amount']


class AdvanceDeductionInline(admin.TabularInline):
    model = AdvanceDeduction
    extra = 0
    readonly_fields = ['salary_advance', 'amount', 'deduction_date']


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'payroll_period', 'basic_salary', 'gross_salary',
        'total_deductions', 'net_salary', 'status', 'is_paid'
    ]
    list_filter = [
        'payroll_period', 'status', 'is_paid', 
        'employee__department', 'calculation_date'
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 
        'employee__employee_id', 'payment_reference'
    ]
    ordering = ['-payroll_period__start_date', 'employee__employee_id']
    
    fieldsets = (
        ('Employee & Period', {
            'fields': ('employee', 'payroll_period')
        }),
        ('Working Days', {
            'fields': ('working_days', 'days_worked', 'days_absent')
        }),
        ('Earnings', {
            'fields': (
                'basic_salary', 'total_allowances', 'overtime_amount', 
                'bonus_amount', 'gross_salary'
            )
        }),
        ('Deductions', {
            'fields': (
                'paye_tax', 'nssf_contribution', 'nhif_contribution',
                'total_other_deductions', 'loan_deductions', 
                'advance_deduction_amount', 'total_deductions'
            )
        }),
        ('Net Pay', {
            'fields': ('net_salary',)
        }),
        ('Status', {
            'fields': ('status', 'calculation_date')
        }),
        ('Payment Information', {
            'fields': (
                'is_paid', 'payment_date', 'payment_reference', 'payment_method'
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )
    
    readonly_fields = [
        'gross_salary', 'total_deductions', 'net_salary', 'calculation_date'
    ]
    
    inlines = [PayrollAllowanceInline, PayrollDeductionInline, AdvanceDeductionInline]
    
    actions = ['calculate_payroll', 'generate_payslips']
    
    def calculate_payroll(self, request, queryset):
        for record in queryset:
            if record.status == 'draft':
                record.calculate_payroll()
                self.message_user(request, f"Payroll calculated for {record.employee}")
            else:
                self.message_user(
                    request,
                    f"Cannot calculate payroll for {record.employee} - already calculated",
                    level='warning'
                )
    calculate_payroll.short_description = "Calculate selected payroll records"
    
    def generate_payslips(self, request, queryset):
        for record in queryset:
            try:
                payslip = record.generate_payslip()
                self.message_user(request, f"Payslip generated: {payslip.payslip_number}")
            except ValueError as e:
                self.message_user(request, str(e), level='error')
    generate_payslips.short_description = "Generate payslips for selected records"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'payroll_period'
        )


@admin.register(OvertimeRecord)
class OvertimeRecordAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'date', 'overtime_hours', 'hourly_rate', 
        'total_amount', 'status', 'approved_by'
    ]
    list_filter = ['status', 'date', 'employee__department']
    search_fields = ['employee__first_name', 'employee__last_name', 'description']
    ordering = ['-date']
    
    fieldsets = (
        ('Employee & Date', {
            'fields': ('employee', 'date')
        }),
        ('Hours & Rate', {
            'fields': (
                'regular_hours', 'overtime_hours', 'overtime_rate', 
                'hourly_rate', 'total_amount'
            )
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Status & Approval', {
            'fields': (
                'status', 'submitted_by', 'approved_by', 'approval_date'
            )
        })
    )
    
    readonly_fields = ['total_amount', 'approval_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'submitted_by', 'approved_by'
        )


@admin.register(BonusRecord)
class BonusRecordAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'payroll_period', 'bonus_type', 'amount', 
        'status', 'is_approved', 'approved_by'
    ]
    list_filter = ['bonus_type', 'status', 'is_approved', 'payroll_period']
    search_fields = ['employee__first_name', 'employee__last_name', 'description']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'payroll_period', 'approved_by'
        )


@admin.register(SalaryAdvance)
class SalaryAdvanceAdmin(admin.ModelAdmin):
    list_display = [
        'advance_number', 'employee', 'amount', 'monthly_deduction',
        'remaining_balance', 'status', 'approval_date'
    ]
    list_filter = ['status', 'approval_date', 'employee__department']
    search_fields = [
        'advance_number', 'employee__first_name', 'employee__last_name', 'reason'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Advance Details', {
            'fields': ('advance_number', 'employee', 'amount', 'reason')
        }),
        ('Repayment Terms', {
            'fields': (
                'monthly_deduction', 'number_of_installments', 'repayment_start_date'
            )
        }),
        ('Tracking', {
            'fields': ('remaining_balance', 'total_repaid', 'status')
        }),
        ('Request & Approval', {
            'fields': (
                'requested_by', 'approved_by', 'approval_date'
            )
        }),
        ('Disbursement', {
            'fields': ('disbursement_date', 'disbursed_by')
        })
    )
    
    readonly_fields = [
        'advance_number', 'remaining_balance', 'total_repaid',
        'approval_date', 'disbursement_date'
    ]
    
    inlines = [AdvanceDeductionInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'requested_by', 'approved_by', 'disbursed_by'
        )


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = [
        'payslip_number', 'get_employee', 'get_period', 'generated_date',
        'download_count', 'last_downloaded'
    ]
    list_filter = ['generated_date', 'last_downloaded']
    search_fields = [
        'payslip_number', 'payroll_record__employee__first_name',
        'payroll_record__employee__last_name'
    ]
    ordering = ['-generated_date']
    
    readonly_fields = [
        'payslip_number', 'generated_date', 'download_count', 'last_downloaded'
    ]
    
    def get_employee(self, obj):
        return obj.payroll_record.employee.get_full_name()
    get_employee.short_description = 'Employee'
    
    def get_period(self, obj):
        return obj.payroll_record.payroll_period.name
    get_period.short_description = 'Period'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'payroll_record__employee', 'payroll_record__payroll_period', 'generated_by'
        )


@admin.register(PayrollReport)
class PayrollReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_name', 'report_type', 'payroll_period', 
        'department', 'employee', 'created_at', 'generated_by'
    ]
    list_filter = ['report_type', 'payroll_period', 'department', 'created_at']
    search_fields = ['report_name', 'file_path']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'payroll_period', 'department', 'employee', 'generated_by'
        )


