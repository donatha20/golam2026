#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan
from apps.core.models import LoanStatusChoices

def main():
    print("=== Loan Status Analysis ===")
    
    # Check total loans
    total_loans = Loan.objects.count()
    print(f"Total loans in database: {total_loans}")
    
    if total_loans == 0:
        print("❌ No loans found in database!")
        return
    
    # Check loans by status
    print("\n=== Loans by Status ===")
    for status_code, status_name in LoanStatusChoices.choices:
        count = Loan.objects.filter(status=status_code).count()
        if count > 0:
            print(f"{status_name}: {count} loans")
    
    # Show loans that should appear for repayment
    print("\n=== Loans that should appear for repayment ===")
    
    # Current API filter
    current_filter_loans = Loan.objects.filter(
        status__in=['disbursed', 'partially_paid']
    ).count()
    print(f"Current API filter (disbursed, partially_paid): {current_filter_loans} loans")
    
    # Better filter including active
    better_filter_loans = Loan.objects.filter(
        status__in=['disbursed', 'active', 'partially_paid']
    ).count()
    print(f"Better filter (disbursed, active, partially_paid): {better_filter_loans} loans")
    
    # Show approved loans that need disbursement
    approved_loans = Loan.objects.filter(status=LoanStatusChoices.APPROVED)
    print(f"\n=== Approved loans waiting for disbursement: {approved_loans.count()} ===")
    
    for loan in approved_loans[:10]:  # Show first 10
        print(f"- {loan.loan_number}: {loan.borrower.get_full_name()}")
        print(f"  Amount: {loan.amount_approved or loan.amount_requested}")
        print(f"  Applied: {loan.application_date}")
        if hasattr(loan, 'approved_date') and loan.approved_date:
            print(f"  Approved: {loan.approved_date}")
    
    # Show sample of each status
    print("\n=== Sample loans by status ===")
    for status_code, status_name in LoanStatusChoices.choices:
        loans = Loan.objects.filter(status=status_code)[:3]
        if loans.exists():
            print(f"\n{status_name} loans:")
            for loan in loans:
                print(f"  - {loan.loan_number}: {loan.borrower.get_full_name()} - {loan.amount_approved or loan.amount_requested}")

if __name__ == '__main__':
    main()
