#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan
from apps.borrowers.models import Borrower

# Get a borrower to test with
borrower = Borrower.objects.filter(status='active').first()

if not borrower:
    print("✗ No active borrower found. Cannot test loan creation.")
else:
    print(f"Testing loan creation with borrower: {borrower.get_full_name()}")
    
    # Create a test loan to verify loan number generation works
    try:
        loan = Loan(
            borrower=borrower,
            loan_type_id=1,  # Assuming loan type 1 exists
            amount_requested=50000,
            interest_rate=10,
            duration_months=12,
            repayment_frequency='monthly',
            repayment_type='monthly',
            status='pending'
        )
        
        # This will trigger generate_loan_number()
        loan_number = loan.generate_loan_number()
        print(f"✓ Generated loan number: {loan_number}")
        
        # Verify it's unique
        existing = Loan.objects.filter(loan_number=loan_number).exists()
        if not existing:
            print(f"✓ Loan number {loan_number} is unique")
        else:
            print(f"✗ Loan number {loan_number} already exists")
            
    except Exception as e:
        print(f"✗ Error during loan number generation: {str(e)}")
