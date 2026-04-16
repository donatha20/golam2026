#!/usr/bin/env python
"""Test repayment recording and balance updates."""

import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from decimal import Decimal
from django.db.models import Sum
from apps.loans.models import Loan, RepaymentSchedule, Repayment, LoanStatusChoices
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

try:
    # Get the first disbursed loan with a repayment schedule
    schedule = RepaymentSchedule.objects.filter(
        loan__status='disbursed'
    ).select_related('loan').first()
    
    if not schedule:
        print("⚠ No disbursed loans with schedules found.")
        sys.exit(0)
    
    loan = schedule.loan
    print(f"📋 Testing with Loan: {loan.loan_number}")
    print(f"   Borrower: {loan.borrower.get_full_name()}")
    print(f"   Outstanding Balance (before): Tsh {loan.outstanding_balance:,.2f}")
    print(f"   Schedule {schedule.installment_number} - Amount Due: Tsh {schedule.amount_due:,.2f}")
    print(f"   Schedule Status: {schedule.get_status_display()}")
    
    # Get the test user
    user = CustomUser.objects.filter(is_staff=True).first()
    if not user:
        user = CustomUser.objects.first()
    
    print(f"\n📝 Simulating payment of Tsh {schedule.amount_due:,.2f}...")
    
    # Create repayment  
    repayment = Repayment.objects.create(
        schedule=schedule,
        amount_paid=schedule.amount_due,
        payment_date='2026-04-14',
        received_by=user
    )
    print(f"✓ Repayment recorded: {repayment.id}")
    print(f"  Amount Paid: Tsh {repayment.amount_paid:,.2f}")
    print(f"  Payment Date: {repayment.payment_date}")
    
    # Update schedule (same as view does)
    schedule.amount_paid = (schedule.amount_paid or Decimal('0')) + repayment.amount_paid
    schedule.save(update_fields=['amount_paid'])
    schedule.update_status()
    print(f"\n✓ Schedule updated")
    print(f"  Schedule Status: {schedule.get_status_display()}")
    print(f"  Schedule Amount Paid: Tsh {schedule.amount_paid:,.2f}/{schedule.amount_due:,.2f}")
    
    # Recalculate loan balance (same as view does)
    total_paid = Repayment.objects.filter(
        schedule__loan=loan
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    
    old_outstanding = loan.outstanding_balance
    loan.total_paid = total_paid
    loan.outstanding_balance = max(Decimal('0'), loan.total_amount - total_paid)
    
    # Update status if loan is paid
    if loan.outstanding_balance <= 0 and loan.status in [
        LoanStatusChoices.ACTIVE,
        LoanStatusChoices.DISBURSED
    ]:
        loan.outstanding_balance = Decimal('0')
        loan.status = LoanStatusChoices.COMPLETED
    
    loan.save(update_fields=['total_paid', 'outstanding_balance', 'status'])
    
    print(f"\n✓ Loan balance updated")
    print(f"  Total Paid: Tsh {loan.total_paid:,.2f}")
    print(f"  Outstanding Balance (after): Tsh {loan.outstanding_balance:,.2f}")
    print(f"  Loan Status: {loan.get_status_display()}")
    print(f"  Balance Reduction: Tsh {(old_outstanding - loan.outstanding_balance):,.2f}")
    
    if loan.outstanding_balance == Decimal('0'):
        print(f"\n✅ Loan fully repaid!")
    elif schedule.amount_paid == schedule.amount_due:
        print(f"\n✅ Installment #{schedule.installment_number} fully paid!")
    else:
        print(f"\n✅ Partial payment recorded!")
    
    print("\n✓ All operations completed successfully!")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
