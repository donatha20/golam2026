#!/usr/bin/env python
"""Test repayment form with payment_type field and verify balance updates."""

import os
import sys
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.forms import RepaymentForm
from apps.loans.models import Loan, RepaymentSchedule
from apps.repayments.models import Repayment
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

print("=" * 70)
print("TESTING REPAYMENT FORM AND BALANCE UPDATES")
print("=" * 70)

# Get a loan with repayment schedule
loan = Loan.objects.filter(status='disbursed').first()
if not loan:
    print("❌ No disbursed loans found in database")
    sys.exit(1)

schedule = RepaymentSchedule.objects.filter(loan=loan, status='pending').first()
if not schedule:
    print("❌ No pending schedules found for disbursed loans")
    sys.exit(1)

print(f"\n✓ Found loan: {loan.loan_number}")
print(f"✓ Outstanding balance: Tsh {loan.outstanding_balance:,.2f}")
print(f"✓ Found schedule: Installment #{schedule.installment_number}")
print(f"✓ Amount due: Tsh {schedule.amount_due:,.2f}")

# Test 1: Form validation with payment_type
print("\n" + "-" * 70)
print("TEST 1: Form field validation")
print("-" * 70)

test_data = {
    'amount_paid': Decimal('50000.00'),
    'payment_date': date.today(),
    'payment_type': 'regular'
}

form = RepaymentForm(data=test_data, schedule=schedule)
if form.is_valid():
    print("✓ Form is valid with payment_type='regular'")
    print(f"  - Amount: {form.cleaned_data['amount_paid']}")
    print(f"  - Date: {form.cleaned_data['payment_date']}")
    print(f"  - Type: {form.cleaned_data['payment_type']}")
else:
    print(f"❌ Form validation failed: {form.errors}")
    sys.exit(1)

# Test 2: Record repayment and check balance updates
print("\n" + "-" * 70)
print("TEST 2: Process repayment and update balances")
print("-" * 70)

initial_balance = loan.outstanding_balance
initial_schedule_paid = schedule.amount_paid or Decimal('0')

# Create and save repayment
repayment = Repayment(
    schedule=schedule,
    loan=loan,
    borrower=loan.borrower,
    amount_paid=Decimal('50000.00'),
    payment_date=date.today(),
    payment_type='regular',
    received_by=CustomUser.objects.first(),
    payment_method='cash',
    status='paid',
    is_verified=True,
    verified_by=CustomUser.objects.first(),
    loan_balance_before=initial_balance,
)
repayment.save()

# Update schedule
schedule.amount_paid = (schedule.amount_paid or Decimal('0')) + repayment.amount_paid
schedule.save(update_fields=['amount_paid'])
schedule.update_status()

# Update loan
total_paid = Repayment.objects.filter(schedule__loan=loan).aggregate(
    total=django.db.models.Sum('amount_paid')
)['total'] or Decimal('0')
loan.total_paid = total_paid
loan.outstanding_balance = loan.total_amount - total_paid
loan.save(update_fields=['total_paid', 'outstanding_balance'])

# Verify updates
repayment.refresh_from_db()
schedule.refresh_from_db()
loan.refresh_from_db()

print(f"✓ Repayment recorded: Tsh {repayment.amount_paid:,.2f}")
print(f"✓ Repayment payment_type: {repayment.payment_type}")
print(f"✓ Schedule status updated to: {schedule.status}")
print(f"✓ Schedule total paid: Tsh {schedule.amount_paid:,.2f}")
print(f"✓ Loan total paid: Tsh {loan.total_paid:,.2f}")
print(f"✓ Loan outstanding balance: Tsh {loan.outstanding_balance:,.2f}")
print(f"✓ Balance reduction: Tsh {initial_balance - loan.outstanding_balance:,.2f}")

if loan.outstanding_balance == initial_balance - Decimal('50000.00'):
    print("\n✅ All balance updates correct!")
else:
    print(f"\n❌ Balance calculation incorrect!")
    print(f"   Expected: {initial_balance - Decimal('50000.00')}")
    print(f"   Got: {loan.outstanding_balance}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
