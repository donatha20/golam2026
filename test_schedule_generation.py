#!/usr/bin/env python
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from apps.loans.models import Loan

# Get the disbursed loan
loan = Loan.objects.get(loan_number='LN202607962013')

print(f"\n=== LOAN DETAILS ===")
print(f"Loan Number: {loan.loan_number}")
print(f"Status: {loan.get_status_display()}")
print(f"Disbursement Date: {loan.disbursement_date}")
print(f"Start Payment Date: {loan.start_payment_date}")
print(f"Duration Months: {loan.duration_months}")
print(f"Total Amount: {loan.total_amount}")
print(f"Repayment Frequency: {loan.get_repayment_frequency_display()}")
print(f"Current Schedule Count: {loan.repayment_schedules.count()}")

print(f"\n=== ATTEMPTING SCHEDULE GENERATION ===")
try:
    loan.generate_repayment_schedule()
    print(f"✓ Schedule generated successfully!")
    print(f"New Schedule Count: {loan.repayment_schedules.count()}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
