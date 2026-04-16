#!/usr/bin/env python
"""Check if there are disbursed loans in the database."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan, LoanStatusChoices

# Count disbursed loans
count = Loan.objects.filter(status=LoanStatusChoices.DISBURSED).count()
print(f"\n✓ Disbursed loans in database: {count}")

# Show first 10
if count > 0:
    print("\nFirst 10 disbursed loans:")
    for loan in Loan.objects.filter(status=LoanStatusChoices.DISBURSED)[:10]:
        borrower_name = loan.borrower.get_full_name() if loan.borrower else "N/A"
        print(f"  - {loan.loan_number}: {borrower_name} | Amount: {loan.total_amount} | Disbursement Date: {loan.disbursement_date}")
else:
    print("\n⚠ No disbursed loans found. Need to create/disburse a loan first.")
    
    # Check for approved loans that can be disbursed
    approved_count = Loan.objects.filter(status=LoanStatusChoices.APPROVED).count()
    print(f"\nApproved loans available for disbursement: {approved_count}")
    
    if approved_count > 0:
        print("First approved loans:")
        for loan in Loan.objects.filter(status=LoanStatusChoices.APPROVED)[:5]:
            borrower_name = loan.borrower.get_full_name() if loan.borrower else "N/A"
            print(f"  - {loan.loan_number}: {borrower_name} | Amount: {loan.amount_approved}")
