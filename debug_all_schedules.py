#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan, RepaymentSchedule

print("=== ALL LOANS ===")
for loan in Loan.objects.all().order_by('-created_at'):
    schedules = RepaymentSchedule.objects.filter(loan=loan)
    print(f"{loan.loan_number}: Status={loan.get_status_display()}, Schedules={schedules.count()}")

print("\n=== REPAYMENT SCHEDULES TABLE ===")
print(f"Total schedules in DB: {RepaymentSchedule.objects.count()}")
for schedule in RepaymentSchedule.objects.all():
    print(f"  Loan: {schedule.loan.loan_number}, Installment: {schedule.installment_number}, Amount: {schedule.amount_due}")
