"""
Views for the payroll app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from decimal import Decimal
import json

from .models import (
    Department, Position, Employee, PayrollPeriod, AllowanceType, DeductionType,
    EmployeeAllowance, EmployeeDeduction, PayrollRecord, OvertimeRecord,
    BonusRecord, SalaryAdvance, Payslip, PayrollReport
)
from .forms import (
    DepartmentForm, PositionForm, EmployeeForm, PayrollPeriodForm,
    AllowanceTypeForm, DeductionTypeForm, EmployeeAllowanceForm,
    EmployeeDeductionForm, OvertimeRecordForm, BonusRecordForm,
    SalaryAdvanceForm, PayrollSearchForm, BulkPayrollActionForm,
    PayrollReportForm
)


@login_required
def payroll_dashboard(request):
    """Payroll dashboard view."""
    context = {
        'total_employees': Employee.objects.filter(status='active').count(),
        'total_departments': Department.objects.filter(is_active=True).count(),
        'pending_payroll_periods': PayrollPeriod.objects.filter(status='draft').count(),
        'pending_advances': SalaryAdvance.objects.filter(status='pending').count(),
        'pending_overtime': OvertimeRecord.objects.filter(status='submitted').count(),
        
        # Recent activities
        'recent_employees': Employee.objects.filter(status='active').order_by('-created_at')[:5],
        'recent_payroll_periods': PayrollPeriod.objects.all().order_by('-created_at')[:5],
        'recent_advances': SalaryAdvance.objects.all().order_by('-created_at')[:5],
    }
    return render(request, 'payroll/dashboard.html', context)


# Department Views
class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'payroll/department_list.html'
    context_object_name = 'departments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Department.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )
        return queryset.order_by('name')


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'payroll/departments/create.html'
    success_url = reverse_lazy('payroll:department_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Department created successfully.')
        return super().form_valid(form)


class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'payroll/departments/update.html'
    success_url = reverse_lazy('payroll:department_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Department updated successfully.')
        return super().form_valid(form)


class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'payroll/departments/detail.html'
    context_object_name = 'department'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = self.object.employees.filter(status='active')
        context['positions'] = self.object.positions.filter(is_active=True)
        return context


# Position Views
class PositionListView(LoginRequiredMixin, ListView):
    model = Position
    template_name = 'payroll/position_list.html'
    context_object_name = 'positions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Position.objects.select_related('department')
        department_id = self.request.GET.get('department')
        search = self.request.GET.get('search')
        
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return queryset.order_by('department__name', 'title')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)
        return context


class PositionCreateView(LoginRequiredMixin, CreateView):
    model = Position
    form_class = PositionForm
    template_name = 'payroll/positions/create.html'
    success_url = reverse_lazy('payroll:position_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Position created successfully.')
        return super().form_valid(form)


class PositionUpdateView(LoginRequiredMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = 'payroll/positions/update.html'
    success_url = reverse_lazy('payroll:position_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Position updated successfully.')
        return super().form_valid(form)


# Employee Views
class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'payroll/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Employee.objects.select_related('department', 'position', 'supervisor')
        
        # Filters
        department_id = self.request.GET.get('department')
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(employee_id__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('employee_id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)
        context['status_choices'] = Employee.STATUS_CHOICES
        return context


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'payroll/employee_form.html'
    success_url = reverse_lazy('payroll:employee_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Employee created successfully.')
        return super().form_valid(form)


class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'payroll/employee_form.html'
    success_url = reverse_lazy('payroll:employee_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Employee updated successfully.')
        return super().form_valid(form)


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'payroll/employees/detail.html'
    context_object_name = 'employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowances'] = self.object.allowances.filter(is_active=True)
        context['deductions'] = self.object.deductions.filter(is_active=True)
        context['recent_payrolls'] = self.object.payroll_records.order_by('-payroll_period__start_date')[:5]
        context['salary_advances'] = self.object.salary_advances.filter(
            status__in=['approved', 'partially_repaid']
        )
        return context


@login_required
@require_http_methods(["POST"])
def employee_deactivate(request, pk):
    """Deactivate an employee."""
    employee = get_object_or_404(Employee, pk=pk)
    termination_date = request.POST.get('termination_date')
    reason = request.POST.get('reason')
    
    if termination_date:
        from datetime import datetime
        termination_date = datetime.strptime(termination_date, '%Y-%m-%d').date()
    
    employee.deactivate(termination_date, reason)
    messages.success(request, f'Employee {employee.get_full_name()} has been deactivated.')
    
    return redirect('payroll:employee_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def employee_reactivate(request, pk):
    """Reactivate an employee."""
    employee = get_object_or_404(Employee, pk=pk)
    employee.reactivate()
    messages.success(request, f'Employee {employee.get_full_name()} has been reactivated.')
    
    return redirect('payroll:employee_detail', pk=pk)


# Payroll Period Views
class PayrollPeriodListView(LoginRequiredMixin, ListView):
    model = PayrollPeriod
    template_name = 'payroll/period_list.html'
    context_object_name = 'periods'
    paginate_by = 20
    
    def get_queryset(self):
        return PayrollPeriod.objects.all().order_by('-start_date')


class PayrollPeriodCreateView(LoginRequiredMixin, CreateView):
    model = PayrollPeriod
    form_class = PayrollPeriodForm
    template_name = 'payroll/period_form.html'
    success_url = reverse_lazy('payroll:period_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Payroll period created successfully.')
        return super().form_valid(form)


class PayrollPeriodDetailView(LoginRequiredMixin, DetailView):
    model = PayrollPeriod
    template_name = 'payroll/periods/detail.html'
    context_object_name = 'period'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payroll_records'] = self.object.payroll_records.select_related(
            'employee', 'employee__department'
        ).order_by('employee__employee_id')
        return context


@login_required
@require_http_methods(["POST"])
def process_payroll_period(request, pk):
    """Process payroll for a specific period."""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    try:
        period.process_payroll(request.user)
        messages.success(request, f'Payroll processed successfully for {period.name}')
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('payroll:period_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def approve_payroll_period(request, pk):
    """Approve processed payroll for a specific period."""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    try:
        period.approve_payroll(request.user)
        messages.success(request, f'Payroll approved successfully for {period.name}')
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('payroll:period_detail', pk=pk)


# Payroll Record Views
@login_required
def payroll_records_list(request):
    """List payroll records with filters."""
    form = PayrollSearchForm(request.GET)
    records = PayrollRecord.objects.select_related(
        'employee', 'employee__department', 'payroll_period'
    )
    
    if form.is_valid():
        if form.cleaned_data['employee']:
            records = records.filter(employee=form.cleaned_data['employee'])
        if form.cleaned_data['department']:
            records = records.filter(employee__department=form.cleaned_data['department'])
        if form.cleaned_data['payroll_period']:
            records = records.filter(payroll_period=form.cleaned_data['payroll_period'])
        if form.cleaned_data['status']:
            records = records.filter(status=form.cleaned_data['status'])
        if form.cleaned_data['date_from']:
            records = records.filter(payroll_period__start_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            records = records.filter(payroll_period__end_date__lte=form.cleaned_data['date_to'])
    
    records = records.order_by('-payroll_period__start_date', 'employee__employee_id')
    
    # Pagination
    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'records': page_obj,
    }
    
    return render(request, 'payroll/payroll_records.html', context)


class PayrollRecordDetailView(LoginRequiredMixin, DetailView):
    model = PayrollRecord
    template_name = 'payroll/records/detail.html'
    context_object_name = 'record'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowances'] = self.object.payroll_allowances.select_related('allowance_type')
        context['deductions'] = self.object.payroll_deductions.select_related('deduction_type')
        context['advance_deductions'] = self.object.advance_deductions.select_related('salary_advance')
        return context


@login_required
@require_http_methods(["POST"])
def calculate_payroll_record(request, pk):
    """Calculate individual payroll record."""
    record = get_object_or_404(PayrollRecord, pk=pk)
    
    try:
        record.calculate_payroll()
        messages.success(request, f'Payroll calculated for {record.employee.get_full_name()}')
    except Exception as e:
        messages.error(request, f'Error calculating payroll: {str(e)}')
    
    return redirect('payroll:record_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def generate_payslip(request, pk):
    """Generate payslip for a payroll record."""
    record = get_object_or_404(PayrollRecord, pk=pk)
    
    try:
        payslip = record.generate_payslip()
        messages.success(request, f'Payslip generated: {payslip.payslip_number}')
        return redirect('payroll:payslip_detail', pk=payslip.pk)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('payroll:record_detail', pk=pk)


# Allowance and Deduction Views
class AllowanceTypeListView(LoginRequiredMixin, ListView):
    model = AllowanceType
    template_name = 'payroll/allowance_types.html'
    context_object_name = 'allowance_types'
    paginate_by = 20


class AllowanceTypeCreateView(LoginRequiredMixin, CreateView):
    model = AllowanceType
    form_class = AllowanceTypeForm
    template_name = 'payroll/allowances/type_create.html'
    success_url = reverse_lazy('payroll:allowance_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Allowance type created successfully.')
        return super().form_valid(form)


class DeductionTypeListView(LoginRequiredMixin, ListView):
    model = DeductionType
    template_name = 'payroll/deduction_types.html'
    context_object_name = 'deduction_types'
    paginate_by = 20


class DeductionTypeCreateView(LoginRequiredMixin, CreateView):
    model = DeductionType
    form_class = DeductionTypeForm
    template_name = 'payroll/deductions/type_create.html'
    success_url = reverse_lazy('payroll:deduction_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Deduction type created successfully.')
        return super().form_valid(form)


class EmployeeAllowanceCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeAllowance
    form_class = EmployeeAllowanceForm
    template_name = 'payroll/allowances/employee_create.html'
    success_url = reverse_lazy('payroll:employee_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Employee allowance added successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('payroll:employee_detail', kwargs={'pk': self.object.employee.pk})


class EmployeeDeductionCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeDeduction
    form_class = EmployeeDeductionForm
    template_name = 'payroll/deductions/employee_create.html'
    success_url = reverse_lazy('payroll:employee_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Employee deduction added successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('payroll:employee_detail', kwargs={'pk': self.object.employee.pk})


# Overtime Views
class OvertimeRecordListView(LoginRequiredMixin, ListView):
    model = OvertimeRecord
    template_name = 'payroll/overtime_list.html'
    context_object_name = 'overtime_records'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = OvertimeRecord.objects.select_related('employee', 'approved_by')
        
        status = self.request.GET.get('status')
        employee_id = self.request.GET.get('employee')
        
        if status:
            queryset = queryset.filter(status=status)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        return queryset.order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(status='active')
        context['status_choices'] = OvertimeRecord.STATUS_CHOICES
        return context


class OvertimeRecordCreateView(LoginRequiredMixin, CreateView):
    model = OvertimeRecord
    form_class = OvertimeRecordForm
    template_name = 'payroll/overtime/create.html'
    success_url = reverse_lazy('payroll:overtime_list')
    
    def form_valid(self, form):
        form.instance.submitted_by = self.request.user
        form.instance.status = 'submitted'
        messages.success(self.request, 'Overtime record created successfully.')
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def approve_overtime(request, pk):
    """Approve overtime record."""
    overtime = get_object_or_404(OvertimeRecord, pk=pk)
    
    if overtime.status == 'submitted':
        overtime.status = 'approved'
        overtime.approved_by = request.user
        overtime.approval_date = timezone.now()
        overtime.save()
        messages.success(request, 'Overtime record approved successfully.')
    else:
        messages.warning(request, 'Overtime record cannot be approved in current status.')
    
    return redirect('payroll:overtime_list')


# Bonus Views
class BonusRecordListView(LoginRequiredMixin, ListView):
    model = BonusRecord
    template_name = 'payroll/bonus_list.html'
    context_object_name = 'bonus_records'
    paginate_by = 20
    
    def get_queryset(self):
        return BonusRecord.objects.select_related('employee', 'payroll_period', 'approved_by').order_by('-created_at')


class BonusRecordCreateView(LoginRequiredMixin, CreateView):
    model = BonusRecord
    form_class = BonusRecordForm
    template_name = 'payroll/bonus/create.html'
    success_url = reverse_lazy('payroll:bonus_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Bonus record created successfully.')
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def approve_bonus(request, pk):
    """Approve bonus record."""
    bonus = get_object_or_404(BonusRecord, pk=pk)
    
    if bonus.status == 'draft':
        bonus.status = 'approved'
        bonus.is_approved = True
        bonus.approved_by = request.user
        bonus.approval_date = timezone.now()
        bonus.save()
        messages.success(request, 'Bonus record approved successfully.')
    else:
        messages.warning(request, 'Bonus record cannot be approved in current status.')
    
    return redirect('payroll:bonus_list')


# Salary Advance Views
class SalaryAdvanceListView(LoginRequiredMixin, ListView):
    model = SalaryAdvance
    template_name = 'payroll/advances/list.html'
    context_object_name = 'advances'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = SalaryAdvance.objects.select_related('employee', 'approved_by')
        
        status = self.request.GET.get('status')
        employee_id = self.request.GET.get('employee')
        
        if status:
            queryset = queryset.filter(status=status)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(status='active')
        context['status_choices'] = SalaryAdvance.STATUS_CHOICES
        return context


class SalaryAdvanceCreateView(LoginRequiredMixin, CreateView):
    model = SalaryAdvance
    form_class = SalaryAdvanceForm
    template_name = 'payroll/advances/create.html'
    success_url = reverse_lazy('payroll:advance_list')
    
    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        messages.success(self.request, 'Salary advance request created successfully.')
        return super().form_valid(form)


class SalaryAdvanceDetailView(LoginRequiredMixin, DetailView):
    model = SalaryAdvance
    template_name = 'payroll/advances/detail.html'
    context_object_name = 'advance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['deductions'] = self.object.deductions.order_by('-deduction_date')
        return context


@login_required
@require_http_methods(["POST"])
def approve_salary_advance(request, pk):
    """Approve salary advance."""
    advance = get_object_or_404(SalaryAdvance, pk=pk)
    
    if advance.status == 'pending':
        advance.status = 'approved'
        advance.approved_by = request.user
        advance.approval_date = timezone.now()
        advance.save()
        messages.success(request, 'Salary advance approved successfully.')
    else:
        messages.warning(request, 'Salary advance cannot be approved in current status.')
    
    return redirect('payroll:advance_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def reject_salary_advance(request, pk):
    """Reject salary advance."""
    advance = get_object_or_404(SalaryAdvance, pk=pk)
    
    if advance.status == 'pending':
        advance.status = 'rejected'
        advance.save()
        messages.success(request, 'Salary advance rejected.')
    else:
        messages.warning(request, 'Salary advance cannot be rejected in current status.')
    
    return redirect('payroll:advance_detail', pk=pk)


# Payslip Views
class PayslipListView(LoginRequiredMixin, ListView):
    model = Payslip
    template_name = 'payroll/payslips/list.html'
    context_object_name = 'payslips'
    paginate_by = 20
    
    def get_queryset(self):
        return Payslip.objects.select_related(
            'payroll_record__employee', 'payroll_record__payroll_period'
        ).order_by('-generated_date')


class PayslipDetailView(LoginRequiredMixin, DetailView):
    model = Payslip
    template_name = 'payroll/payslips/detail.html'
    context_object_name = 'payslip'


@login_required
def download_payslip(request, pk):
    """Download payslip as PDF."""
    payslip = get_object_or_404(Payslip, pk=pk)
    payslip.record_download()
    
    # Here you would generate and return the PDF
    # For now, redirect to detail view
    messages.info(request, 'Payslip download functionality to be implemented.')
    return redirect('payroll:payslip_detail', pk=pk)


# AJAX Views for dynamic forms
@login_required
def get_positions_by_department(request):
    """Get positions for a specific department (AJAX)."""
    department_id = request.GET.get('department_id')
    positions = Position.objects.filter(
        department_id=department_id, is_active=True
    ).values('id', 'title')
    
    return JsonResponse({'positions': list(positions)})


@login_required
def get_employee_salary_info(request):
    """Get employee salary information for advance calculations (AJAX)."""
    employee_id = request.GET.get('employee_id')
    try:
        employee = Employee.objects.get(id=employee_id)
        data = {
            'basic_salary': float(employee.basic_salary),
            'max_advance': float(employee.basic_salary * 3),
            'max_monthly_deduction': float(employee.basic_salary * Decimal('0.30')),
        }
        return JsonResponse(data)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)


# Report Views
@login_required
def payroll_reports(request):
    """Payroll reports page."""
    if request.method == 'POST':
        form = PayrollReportForm(request.POST)
        if form.is_valid():
            # Generate report logic here
            messages.success(request, 'Report generated successfully.')
            return redirect('payroll:reports')
    else:
        form = PayrollReportForm()
    context = {
        'form': form,
        'recent_reports': PayrollReport.objects.order_by('-created_at')[:10]
    }
    return render(request, 'payroll/reports.html', context)


# AJAX report generation view
from django.views.decorators.csrf import csrf_exempt
@login_required
@require_http_methods(["POST"])
@csrf_exempt
def generate_report(request):
    """Generate payroll report for AJAX requests."""
    report_type = request.POST.get('report_type')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    department_id = request.POST.get('department')
    employee_id = request.POST.get('employee')

    html = ""
    title = "Payroll Report"
    records = PayrollRecord.objects.select_related('employee', 'payroll_period')

    # Filter by date
    if start_date:
        records = records.filter(payroll_period__start_date__gte=start_date)
    if end_date:
        records = records.filter(payroll_period__end_date__lte=end_date)
    if department_id:
        records = records.filter(employee__department_id=department_id)
    if employee_id:
        records = records.filter(employee_id=employee_id)

    if report_type == 'employee_summary':
        title = "Employee Summary"
        employees = Employee.objects.all()
        html += f"<h4>Total Employees: {employees.count()}</h4>"
        html += "<ul>"
        for emp in employees:
            html += f"<li>{emp.get_full_name()} - {emp.department.name if emp.department else '-'} - {emp.status}</li>"
        html += "</ul>"
    elif report_type == 'payroll_summary':
        title = "Payroll Summary"
        total_gross = records.aggregate(Sum('gross_pay'))['gross_pay__sum'] or 0
        total_net = records.aggregate(Sum('net_pay'))['net_pay__sum'] or 0
        html += f"<h4>Total Gross Pay: {total_gross:,.2f}</h4>"
        html += f"<h4>Total Net Pay: {total_net:,.2f}</h4>"
        html += f"<p>Records: {records.count()}</p>"
    elif report_type == 'tax_summary':
        title = "Tax Summary"
        total_paye = records.aggregate(Sum('paye_tax'))['paye_tax__sum'] or 0
        total_nssf = records.aggregate(Sum('nssf_deduction'))['nssf_deduction__sum'] or 0
        total_nhif = records.aggregate(Sum('nhif_deduction'))['nhif_deduction__sum'] or 0
        html += f"<h4>Total PAYE: {total_paye:,.2f}</h4>"
        html += f"<h4>Total NSSF: {total_nssf:,.2f}</h4>"
        html += f"<h4>Total NHIF: {total_nhif:,.2f}</h4>"
        html += f"<p>Records: {records.count()}</p>"
    else:
        html += "<p>No report type selected.</p>"

    return JsonResponse({
        'success': True,
        'title': title,
        'html': html,
    })


# Bulk Actions
@login_required
@require_http_methods(["POST"])
def bulk_payroll_actions(request):
    """Handle bulk payroll actions."""
    action = request.POST.get('action')
    record_ids = request.POST.getlist('record_ids')
    
    if not record_ids:
        messages.warning(request, 'No records selected.')
        return redirect('payroll:record_list')
    
    records = PayrollRecord.objects.filter(id__in=record_ids)
    
    if action == 'calculate':
        for record in records:
            if record.status == 'draft':
                record.calculate_payroll()
        messages.success(request, f'Calculated payroll for {records.count()} records.')
    
    elif action == 'generate_payslips':
        for record in records:
            try:
                record.generate_payslip()
            except ValueError:
                pass
        messages.success(request, f'Generated payslips for applicable records.')
    
    elif action == 'mark_paid':
        records.filter(status='approved').update(
            is_paid=True,
            payment_date=timezone.now()
        )
        messages.success(request, f'Marked {records.count()} records as paid.')
    
    return redirect('payroll:record_list')
