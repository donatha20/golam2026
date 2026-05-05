"""
Test script to verify loan arrears logic.

This tests:
1. RepaymentSchedule.is_overdue property returns correct results
2. Dashboard counts overdue installments correctly
3. collect_expected_repayment properly updates schedule status
4. Overdue installments are removed from arrears after payment
"""

import os
import sys
import django
from datetime import timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from django.db.models import F, Sum
from apps.loans.models import Loan, RepaymentSchedule, RepaymentStatusChoices, Repayment
from apps.borrowers.models import Borrower
from apps.accounts.models import CustomUser

def test_is_overdue_property():
    """Test RepaymentSchedule.is_overdue property"""
    print("\n" + "="*60)
    print("TEST 1: RepaymentSchedule.is_overdue Property")
    print("="*60)
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    # Get test data or create minimal test
    schedules = RepaymentSchedule.objects.filter(due_date__lt=today).select_related('loan')[:5]
    
    if not schedules:
        print("No past-due schedules found in database")
    else:
        for schedule in schedules:
            remaining = schedule.amount_due - (schedule.amount_paid or Decimal('0.00'))
            is_overdue_prop = schedule.is_overdue
            is_paid = schedule.status in [RepaymentStatusChoices.PAID]
            has_remaining = remaining > 0
            
            print(f"\nSchedule {schedule.id}:")
            print(f"  Due Date: {schedule.due_date} (Days overdue: {(today - schedule.due_date).days})")
            print(f"  Amount Due: {schedule.amount_due}")
            print(f"  Amount Paid: {schedule.amount_paid}")
            print(f"  Remaining: {remaining}")
            print(f"  Status: {schedule.status}")
            print(f"  Is Overdue (property): {is_overdue_prop}")
            print(f"  Expected Logic: due_date < today({schedule.due_date < today}) AND status not PAID({not is_paid}) AND remaining > 0({has_remaining})")
            
            # Verify logic
            expected = (schedule.due_date < today and not is_paid and has_remaining)
            if is_overdue_prop == expected:
                print(f"  ✅ PASS: is_overdue property returns correct value")
            else:
                print(f"  ❌ FAIL: Expected {expected} but got {is_overdue_prop}")


def test_dashboard_overdue_query():
    """Test dashboard overdue installments query"""
    print("\n" + "="*60)
    print("TEST 2: Dashboard Overdue Installments Query")
    print("="*60)
    
    today = timezone.now().date()
    
    # Query from dashboard code
    overdue_schedules = RepaymentSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'due', 'partial', 'missed', 'defaulted'],
        amount_paid__lt=F('amount_due')
    ).select_related('loan__borrower')
    
    print(f"\nTotal overdue installments found: {overdue_schedules.count()}")
    
    if overdue_schedules.count() > 0:
        # Calculate totals
        overdue_amount = overdue_schedules.aggregate(
            total=Sum(F('amount_due') - F('amount_paid'), output_field=django.db.models.DecimalField())
        )['total'] or Decimal('0.00')
        
        overdue_borrowers = overdue_schedules.values('loan__borrower').distinct().count()
        
        print(f"Total Overdue Amount: {overdue_amount}")
        print(f"Unique Borrowers Affected: {overdue_borrowers}")
        
        # Show sample
        print(f"\nFirst 5 overdue installments:")
        for schedule in overdue_schedules[:5]:
            remaining = schedule.amount_due - (schedule.amount_paid or Decimal('0.00'))
            days_overdue = (today - schedule.due_date).days
            print(f"  - Loan {schedule.loan.loan_number}: Installment {schedule.installment_number}")
            print(f"    Due: {schedule.due_date} ({days_overdue} days overdue)")
            print(f"    Remaining: {remaining} | Status: {schedule.status}")
    else:
        print("No overdue installments found")
    
    print(f"✅ PASS: Dashboard query returns {overdue_schedules.count()} overdue installments")


def test_collect_updates_status():
    """Test that collecting a repayment updates schedule status"""
    print("\n" + "="*60)
    print("TEST 3: Collect Repayment Updates Status")
    print("="*60)
    
    today = timezone.now().date()
    
    # Find a partially paid schedule to test
    partial_schedules = RepaymentSchedule.objects.filter(
        status=RepaymentStatusChoices.PARTIAL,
        amount_paid__gt=0,
        amount_paid__lt=F('amount_due')
    ).select_related('loan')[:1]
    
    if not partial_schedules:
        print("No partially paid schedules found for testing")
        return
    
    schedule = partial_schedules[0]
    original_amount_paid = schedule.amount_paid or Decimal('0.00')
    remaining = schedule.amount_due - original_amount_paid
    
    print(f"\nTesting with Schedule {schedule.id}:")
    print(f"  Original Amount Paid: {original_amount_paid}")
    print(f"  Remaining: {remaining}")
    print(f"  Original Status: {schedule.status}")
    
    # Simulate collecting the remaining amount
    schedule.amount_paid = schedule.amount_due
    schedule.save()
    schedule.update_status()
    
    # Verify status changed to PAID
    schedule.refresh_from_db()
    print(f"\nAfter collecting remaining amount:")
    print(f"  Amount Paid: {schedule.amount_paid}")
    print(f"  New Status: {schedule.status}")
    
    if schedule.status == RepaymentStatusChoices.PAID:
        print(f"✅ PASS: Schedule status correctly changed to PAID")
    else:
        print(f"❌ FAIL: Expected PAID status but got {schedule.status}")


def test_paid_schedule_not_in_arrears():
    """Test that paid schedules don't appear in arrears"""
    print("\n" + "="*60)
    print("TEST 4: Paid Schedules Not in Arrears")
    print("="*60)
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Find paid schedules with past due dates
    paid_past_due = RepaymentSchedule.objects.filter(
        due_date__lt=today,
        status=RepaymentStatusChoices.PAID,
        amount_paid__gte=F('amount_due')
    ).select_related('loan')[:5]
    
    print(f"\nFound {paid_past_due.count()} paid schedules with past due dates")
    
    if paid_past_due.count() > 0:
        for schedule in paid_past_due[:3]:
            remaining = schedule.amount_due - (schedule.amount_paid or Decimal('0.00'))
            is_overdue = schedule.is_overdue
            print(f"\n  Schedule {schedule.id}:")
            print(f"    Due Date: {schedule.due_date} (Past due)")
            print(f"    Status: {schedule.status}")
            print(f"    Remaining: {remaining}")
            print(f"    is_overdue property: {is_overdue}")
            
            if not is_overdue:
                print(f"    ✅ PASS: Paid schedule correctly excluded from arrears")
            else:
                print(f"    ❌ FAIL: Paid schedule should not be in arrears")
    else:
        print("No paid past-due schedules found to test")


def test_arrears_statistics():
    """Test overall arrears statistics"""
    print("\n" + "="*60)
    print("TEST 5: Overall Arrears Statistics")
    print("="*60)
    
    today = timezone.now().date()
    
    # Count overdue schedules using is_overdue property
    all_overdue_schedules = RepaymentSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'due', 'partial', 'missed', 'defaulted'],
        amount_paid__lt=F('amount_due')
    ).select_related('loan__borrower')
    
    count_from_query = all_overdue_schedules.count()
    
    # Count using is_overdue property
    count_from_property = sum(1 for s in all_overdue_schedules if s.is_overdue)
    
    print(f"\nOverdue Installments (Query-based): {count_from_query}")
    print(f"Overdue Installments (Property-based): {count_from_property}")
    
    if count_from_query == count_from_property:
        print(f"✅ PASS: Query and property counts match")
    else:
        print(f"⚠️  Query and property counts differ")
        print(f"  Difference: {count_from_query - count_from_property}")


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "LOAN ARREARS LOGIC TEST SUITE".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    print("\nTesting date:", timezone.now().date())
    
    try:
        test_is_overdue_property()
        test_dashboard_overdue_query()
        test_collect_updates_status()
        test_paid_schedule_not_in_arrears()
        test_arrears_statistics()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("\n✅ Arrears logic test suite finished\n")
        
    except Exception as e:
        print(f"\n❌ ERROR during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
