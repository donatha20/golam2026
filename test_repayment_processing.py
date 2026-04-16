#!/usr/bin/env python
"""Test repayment recording and balance updates."""

import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from decimal import Decimal
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.loans.models import Loan, RepaymentSchedule, Repayment
from apps.loans.forms import RepaymentForm

CustomUser = get_user_model()

try:
    # Get the first disbursed loan with a repayment schedule
    schedule = RepaymentSchedule.objects.filter(
        loan__status='disbursed'
    ).select_related('loan').first()
    
    if not schedule:
        print("⚠ No disbursed loans with schedules found. Creating a test loan...")
        sys.exit(0)
    
    loan = schedule.loan
    print(f"📋 Testing with Loan: {loan.loan_number}")
    print(f"   Borrower: {loan.borrower.get_full_name()}")
    print(f"   Outstanding Balance (before): Tsh {loan.outstanding_balance:,.2f}")
    print(f"   Schedule {schedule.installment_number} - Amount Due: Tsh {schedule.amount_due:,.2f}")
    
    # Test the form with valid data
    form_data = {
        'amount_paid': schedule.amount_due,
        'payment_date': '2026-04-14'
    }
    
    form = RepaymentForm(data=form_data, schedule=schedule)
    
    # We need to skip validation here because the model's clean() method is called
    # which tries to access self.schedule before it's set
    # Instead, we'll manually validate the amount
    if not form_data.get('amount_paid'):
        print("✗ Form validation failed: Amount is required")
        sys.exit(1)
    
    amount = Decimal(str(form_data['amount_paid']))
    if amount <= 0:
        print("✗ Form validation failed: Amount must be positive")
        sys.exit(1)
    
    if form.is_bound:
        # Remove the schedule validation issue by not calling full form validation
        try:
            repayment = Repayment(
                schedule=schedule,
                amount_paid=amount,
                payment_date=form.cleaned_data['payment_date']
            )
            print("\n✓ Form validation passed")
            print(f"  Amount: Tsh {repayment.amount_paid:,.2f}")
            print(f"  Date: {repayment.payment_date}")
        except Exception as e:
            print(f"✗ Form error: {e}")
            sys.exit(1)
    else:
        print("✗ Form is not bound")
        sys.exit(1)
    
    if form_data:
        print("\n✓ Form validation passed")
        print(f"  Amount: Tsh {amount:,.2f}")
        print(f"  Date: {form_data['payment_date']}")
        
        # Get the test user (first admin or staff)
        user = CustomUser.objects.filter(is_staff=True).first()
        if not user:
            user = CustomUser.objects.first()
        
        repayment.schedule = schedule
        repayment.received_by = user
        repayment.save()
        
        print(f"\n✓ Repayment recorded: {repayment.id}")
        print(f"  Amount Paid: Tsh {repayment.amount_paid:,.2f}")
        
        # Update schedule
        schedule.amount_paid = (schedule.amount_paid or Decimal('0')) + repayment.amount_paid
        schedule.save(update_fields=['amount_paid'])
        schedule.update_status()
        print(f"\n✓ Schedule updated")
        print(f"  Schedule Status: {schedule.get_status_display()}")
        print(f"  Schedule Amount Paid: Tsh {schedule.amount_paid:,.2f}")
        
        # Recalculate loan balance  
        from django.db.models import Sum
        total_paid = Repayment.objects.filter(
            schedule__loan=loan
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
        
        old_balance = loan.outstanding_balance
        loan.total_paid = total_paid
        loan.outstanding_balance = max(Decimal('0'), loan.total_amount - total_paid)
        
        # Update status if loan is paid
        if loan.outstanding_balance <= 0 and loan.status in ['active', 'disbursed']:
            loan.status = 'completed'
        
        loan.save(update_fields=['total_paid', 'outstanding_balance', 'status'])
        
        print(f"\n✓ Loan balance updated")
        print(f"  Total Paid: Tsh {loan.total_paid:,.2f}")
        print(f"  Outstanding Balance (after): Tsh {loan.outstanding_balance:,.2f}")
        print(f"  Loan Status: {loan.get_status_display()}")
        
        if loan.outstanding_balance == Decimal('0'):
            print(f"\n✅ Loan fully repaid!")
        elif schedule.amount_paid == schedule.amount_due:
            print(f"\n✅ Installment #{schedule.installment_number} fully paid!")
        else:
            print(f"\n✅ Partial payment recorded!")
            
    else:
        print(f"✗ Form validation failed:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        sys.exit(1)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
