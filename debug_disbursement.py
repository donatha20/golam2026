#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan

# Check loan statuses
print("=== ALL LOANS STATUS ===")
for loan in Loan.objects.all().order_by('-created_at'):
    print(f"\n{loan.loan_number}:")
    print(f"  Status: {loan.get_status_display()}")
    print(f"  Amount Approved: {loan.amount_approved}")
    print(f"  Created: {loan.created_at}")
    print(f"  Approved Date: {loan.approval_date}")
    print(f"  Disbursement Date: {loan.disbursement_date}")
    print(f"  Repayment Schedule Count: {loan.repayment_schedule.count()}")

print("\n=== LOAN COUNT BY STATUS ===")
for status_code, status_name in Loan.STATUS_CHOICES:
    count = Loan.objects.filter(status=status_code).count()
    print(f"{status_name}: {count}")
