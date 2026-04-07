"""
URL patterns for loan management.
"""
from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # API endpoints
    path('api/borrowers/', views.borrowers_api, name='borrowers_api'),
    path('api/borrowers/search/', views.borrower_search_api, name='borrower_search_api'),
    path('api/borrowers/with-loans/', views.borrowers_with_loans_api, name='borrowers_with_loans_api'),
    path('api/loans/borrower/<int:borrower_id>/active/', views.borrower_loans_api, name='borrower_loans_api'),
    
    # Main Views - Using Class-Based Views where available
    path('', views.DisbursedLoanListView.as_view(), name='disbursed_loans'),
   
    path('disbursed/', views.DisbursedLoanListView.as_view(), name='disbursed_loans_list'),
    path('expected-repayments/', views.ExpectedRepaymentsView.as_view(), name='expected_repayments'),
    path('repaid/', views.RepaidLoansView.as_view(), name='repaid_loans'),
    path('non-performing/', views.NonPerformingLoansView.as_view(), name='non_performing_loans'),
    
    # Function-Based Views that exist
    path('add/', views.add_new_loan, name='add_loan'),
    path('<int:loan_id>/edit/', views.edit_loan, name='edit_loan'),
    path('<int:loan_id>/delete/', views.delete_loan, name='delete_loan'),
    path('add-group/', views.add_group_loan, name='add_group_loan'),
    path('repayments/<int:loan_id>/', views.loan_repayments, name='loan_repayments'),
    path('repayments/record/<int:schedule_id>/', views.record_repayment, name='record_repayment'),
    path('repayments/group/<int:schedule_id>/', views.record_group_repayment, name='record_group_repayment'),
    path('repayments/rollover/<int:schedule_id>/', views.rollover_repayment, name='rollover_repayment'),
    path('approval/<int:loan_id>/', views.loan_approval, name='loan_approval'),
    path('rejection/<int:loan_id>/', views.loan_rejection, name='loan_rejection'),
    path('disbursement/<int:loan_id>/', views.loan_disbursement, name='loan_disbursement'),
    path('nearing-last/', views.nearing_last_installments, name='loans_approaching_last_installment'),
    path('interest-summary/', views.interest_summary, name='interest_summary'),
    path('receivables/', views.receivables_view, name='interest_receivables'),
    path('missed-repayments-interest/', views.missed_repayments_interest, name='missed_repayments_interest'),
    path('<int:loan_id>/', views.loan_detail, name='loan_detail'),
    
    # Views for templates that exist but need implementations
    path('outstanding/', views.outstanding_loans, name='outstanding_loans'),
    path('fully-paid/', views.fully_paid_loans, name='fully_paid_loans'),
    path('defaulted/', views.defaulted_loans, name='defaulted_loans'),
    path('written-off/', views.written_off_loans, name='written_off_loans'),
    path('redisbursed/', views.redisbursed_loans, name='redisbursed_loans'),
    path('penalties/', views.penalties, name='penalties'),
    path('penalties/clear/', views.clear_penalties, name='clear_penalties'),
    path('portfolio-at-risk/', views.portfolio_at_risk, name='portfolio_at_risk'),
    path('customer-portfolio/', views.customer_portfolio, name='customer_portfolio'),
    path('customer-portfolio/export/', views.export_customer_portfolio, name='export_customer_portfolio'),
    path('summary-by-age-gender/', views.summary_by_age_and_gender, name='summary_by_age_gender'),  # FIXED
    path('summary-by-portfolio/', views.summary_by_portfolio, name='summary_by_portfolio'),
    path('loans-graphs-summary/', views.loans_graphs_summary, name='loans_graphs_summary'),  # FIXED
    path('loans-arrears/', views.loans_arrears, name='loans_arrears'),
    path('loans-ageing/', views.loans_ageing, name='loans_ageing'),
    path('missed-payments/', views.missed_payments, name='missed_payments'),
    path('missed-schedules/', views.missed_schedules, name='missed_schedules'),
    path('record-old-loans/', views.record_old_loans, name='record_old_loans'),
    path('rollover-repayments/', views.rollover_repayments, name='rollover_repayments'),
    path('create-schedules/', views.create_schedules, name='create_schedules'),
    path('create-group-schedules/', views.create_group_schedules, name='create_group_schedules'),
    path('interest/calculator/', views.test_interest_calculator, name='test_interest_calculators'),  # FIXED
    
    # Additional views that exist in views.py but weren't in urls.py
    path('penalties/add/', views.add_penalty_form, name='add_penalty'),  # Added missing add_penalty URL
    path('penalties/apply/<int:schedule_id>/', views.apply_penalty, name='apply_penalty'),
    path('penalties/applied/', views.applied_penalties, name='applied_penalties'),
    path('write-off/<int:loan_id>/', views.write_off_loan, name='write_off_loan'),
    path('import-old-loan/', views.import_old_loan, name='import_old_loan'),
    path('old-loans/', views.old_loans_list, name='old_loans_list'),
    path('group-schedule/create/<int:group_loan_id>/', views.create_group_schedule, name='create_group_schedule'),
    path('group-schedules/', views.group_schedules, name='group_schedules'),
    path('group-loans/', views.group_loans, name='group_loans'),
    path('group-loans/<int:group_loan_id>/edit/', views.edit_group_loan, name='edit_group_loan'),
    path('group-loans/<int:group_loan_id>/delete/', views.delete_group_loan, name='delete_group_loan'),

    # Adding a placeholder for loan_list view
    path('list/', views.loan_list, name='loan_list'),
    path('pending/', views.pending_loans_list, name='pending_loans'),
    path('approved/', views.approved_loans_list, name='approved_loans'),
    path('rejected/', views.rejected_loans_list, name='rejected_loans'),

    # Export views
    path('export/loans/pdf/', views.export_loans_pdf, name='export_loans_pdf'),
    path('export/loans/excel/', views.export_loans_excel, name='export_loans_excel'),
    path('export/portfolio-analysis/pdf/', views.export_portfolio_analysis_pdf, name='export_portfolio_analysis_pdf'),
    path('export/overdue/pdf/', views.export_overdue_loans_pdf, name='export_overdue_loans_pdf'),
    path('export/overdue/excel/', views.export_overdue_loans_excel, name='export_overdue_loans_excel'),
]

