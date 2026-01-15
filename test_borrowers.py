#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.borrowers.models import Borrower, BorrowerStatus
from apps.loans.models import Loan

def main():
    print("=== Borrower Database Test ===")
    
    # Check total borrowers
    total_borrowers = Borrower.objects.count()
    print(f"Total borrowers in database: {total_borrowers}")
    
    if total_borrowers == 0:
        print("❌ No borrowers found in database!")
        return
    
    # Check status values
    all_statuses = list(Borrower.objects.values_list('status', flat=True).distinct())
    print(f"All borrower status values: {all_statuses}")
    
    # Check active borrowers
    active_borrowers = Borrower.objects.filter(status=BorrowerStatus.ACTIVE).count()
    print(f"Active borrowers: {active_borrowers}")
    
    # Check borrowers with loans
    borrowers_with_loans = Borrower.objects.filter(
        loans__status__in=['disbursed', 'partially_paid']
    ).distinct().count()
    print(f"Borrowers with active loans: {borrowers_with_loans}")
    
    # Show sample borrowers
    print("\n=== Sample Borrowers ===")
    for borrower in Borrower.objects.all()[:5]:
        print(f"- {borrower.get_full_name()} ({borrower.borrower_id}) - Status: {borrower.status}")
        loans_count = borrower.loans.count()
        print(f"  Loans: {loans_count}")
        if loans_count > 0:
            for loan in borrower.loans.all()[:2]:
                print(f"    - Loan {loan.loan_number}: {loan.status}")
    
    print("\n=== Testing API Logic ===")
    # Test the same logic as the API
    try:
        borrowers = Borrower.objects.filter(status='active')
        borrowers = borrowers.filter(
            loans__status__in=['disbursed', 'partially_paid']
        ).distinct()
        
        print(f"API would return {borrowers.count()} borrowers")
        
        for borrower in borrowers[:3]:
            print(f"- {borrower.get_full_name()}")
            
    except Exception as e:
        print(f"❌ Error in API logic: {e}")

if __name__ == '__main__':
    main()
