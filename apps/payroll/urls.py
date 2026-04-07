"""
URL configuration for the payroll app.
"""
from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    # Dashboard
    path('', views.payroll_dashboard, name='dashboard'),
    
    # Department URLs
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:pk>/update/', views.DepartmentUpdateView.as_view(), name='department_update'),
    
    # Position URLs
    path('positions/', views.PositionListView.as_view(), name='position_list'),
    path('positions/create/', views.PositionCreateView.as_view(), name='position_create'),
    path('positions/<int:pk>/update/', views.PositionUpdateView.as_view(), name='position_update'),
    
    # Employee URLs
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/update/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/deactivate/', views.employee_deactivate, name='employee_deactivate'),
    path('employees/<int:pk>/reactivate/', views.employee_reactivate, name='employee_reactivate'),
    
    # Payroll Period URLs
    path('periods/', views.PayrollPeriodListView.as_view(), name='period_list'),
    path('periods/create/', views.PayrollPeriodCreateView.as_view(), name='period_create'),
    path('periods/<int:pk>/', views.PayrollPeriodDetailView.as_view(), name='period_detail'),
    path('periods/<int:pk>/process/', views.process_payroll_period, name='period_process'),
    path('periods/<int:pk>/approve/', views.approve_payroll_period, name='period_approve'),
    
    # Payroll Record URLs
    path('records/', views.payroll_records_list, name='record_list'),
    path('records/<int:pk>/', views.PayrollRecordDetailView.as_view(), name='record_detail'),
    path('records/<int:pk>/calculate/', views.calculate_payroll_record, name='record_calculate'),
    path('records/<int:pk>/payslip/', views.generate_payslip, name='record_generate_payslip'),
    path('records/bulk-actions/', views.bulk_payroll_actions, name='bulk_actions'),
    
    # Allowance URLs
    path('allowances/types/', views.AllowanceTypeListView.as_view(), name='allowance_type_list'),
    path('allowances/types/create/', views.AllowanceTypeCreateView.as_view(), name='allowance_type_create'),
    path('allowances/employee/create/', views.EmployeeAllowanceCreateView.as_view(), name='employee_allowance_create'),
    
    # Deduction URLs
    path('deductions/types/', views.DeductionTypeListView.as_view(), name='deduction_type_list'),
    path('deductions/types/create/', views.DeductionTypeCreateView.as_view(), name='deduction_type_create'),
    path('deductions/employee/create/', views.EmployeeDeductionCreateView.as_view(), name='employee_deduction_create'),
    
    # Overtime URLs
    path('overtime/', views.OvertimeRecordListView.as_view(), name='overtime_list'),
    path('overtime/create/', views.OvertimeRecordCreateView.as_view(), name='overtime_create'),
    path('overtime/<int:pk>/approve/', views.approve_overtime, name='overtime_approve'),
    
    # Bonus URLs
    path('bonuses/', views.BonusRecordListView.as_view(), name='bonus_list'),
    path('bonuses/create/', views.BonusRecordCreateView.as_view(), name='bonus_create'),
    path('bonuses/<int:pk>/approve/', views.approve_bonus, name='bonus_approve'),
    
    # Salary Advance URLs
    path('advances/', views.SalaryAdvanceListView.as_view(), name='advance_list'),
    path('advances/create/', views.SalaryAdvanceCreateView.as_view(), name='advance_create'),
    path('advances/<int:pk>/', views.SalaryAdvanceDetailView.as_view(), name='advance_detail'),
    path('advances/<int:pk>/approve/', views.approve_salary_advance, name='advance_approve'),
    path('advances/<int:pk>/reject/', views.reject_salary_advance, name='advance_reject'),
    
    # Payslip URLs
    path('payslips/', views.PayslipListView.as_view(), name='payslip_list'),
    path('payslips/<int:pk>/', views.PayslipDetailView.as_view(), name='payslip_detail'),
    path('payslips/<int:pk>/download/', views.download_payslip, name='payslip_download'),
    
    # Report URLs
    path('reports/', views.payroll_reports, name='reports'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # AJAX URLs
    path('ajax/positions/', views.get_positions_by_department, name='ajax_positions'),
    path('ajax/employee-salary/', views.get_employee_salary_info, name='ajax_employee_salary'),
]


