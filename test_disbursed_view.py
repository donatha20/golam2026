#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan
from apps.core.models import LoanStatusChoices

print("=== CHECKING DISBURSED LOANS VIEW QUERY ===\n")

# Exact query from the view
queryset = Loan.objects.filter(
    status=LoanStatusChoices.DISBURSED
).select_related("borrower", "disbursed_by", "loan_type")

print(f"Query: {queryset.query}")
print(f"\nTotal count: {queryset.count()}")

print("\n=== LOANS RETURNED BY QUERY ===")
for loan in queryset:
    print(f"\n{loan.loan_number}:")
    print(f"  Status: {loan.get_status_display()}")
    print(f"  Borrower: {loan.borrower.get_full_name()}")
    print(f"  Amount: {loan.amount_approved}")
    print(f"  Disbursed: {loan.disbursement_date}")
    print(f"  Disbursed By: {loan.disbursed_by.username if loan.disbursed_by else 'N/A'}")
