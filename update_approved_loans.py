#!/usr/bin/env python
"""
Script to update existing approved loans to disbursed status.
This should be run once to migrate existing approved loans.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan, LoanDisbursement
from apps.core.models import LoanStatusChoices
from django.utils import timezone
from django.db import transaction

def update_approved_loans():
    """Update all approved loans to disbursed status."""
    
    print("=== Updating Approved Loans to Disbursed Status ===")
    
    # Find all approved loans
    approved_loans = Loan.objects.filter(status=LoanStatusChoices.APPROVED)
    total_approved = approved_loans.count()
    
    print(f"Found {total_approved} approved loans to update")
    
    if total_approved == 0:
        print("✅ No approved loans found. Nothing to update.")
        return
    
    updated_count = 0
    
    # Process each approved loan
    for loan in approved_loans:
        try:
            with transaction.atomic():
                print(f"\nProcessing loan {loan.loan_number} for {loan.borrower.get_full_name()}")
                
                # Update loan status to disbursed
                loan.status = LoanStatusChoices.DISBURSED
                
                # Set disbursement details
                if not loan.disbursement_date:
                    loan.disbursement_date = loan.approval_date or timezone.now().date()
                
                if not loan.disbursed_by:
                    loan.disbursed_by = loan.approved_by
                
                loan.save()
                
                # Create disbursement record if it doesn't exist
                disbursement, created = LoanDisbursement.objects.get_or_create(
                    loan=loan,
                    defaults={
                        'disbursement_date': loan.disbursement_date,
                        'amount': loan.amount_approved,
                        'disbursed_by': loan.disbursed_by or loan.approved_by,
                        'notes': 'Auto-migrated from approved status'
                    }
                )
                
                if created:
                    print(f"  ✅ Created disbursement record")
                else:
                    print(f"  ℹ️  Disbursement record already exists")
                
                # Generate repayment schedule if it doesn't exist
                try:
                    from apps.loans.views import _generate_repayment_schedule
                    
                    # Check if schedule already exists
                    if not loan.repayment_schedules.exists():
                        _generate_repayment_schedule(loan)
                        print(f"  ✅ Generated repayment schedule")
                    else:
                        print(f"  ℹ️  Repayment schedule already exists")
                        
                except Exception as e:
                    print(f"  ⚠️  Could not generate repayment schedule: {e}")
                
                print(f"  ✅ Updated loan {loan.loan_number} to disbursed status")
                updated_count += 1
                
        except Exception as e:
            print(f"  ❌ Error updating loan {loan.loan_number}: {e}")
            continue
    
    print(f"\n=== Summary ===")
    print(f"Total approved loans found: {total_approved}")
    print(f"Successfully updated: {updated_count}")
    print(f"Failed to update: {total_approved - updated_count}")
    
    if updated_count > 0:
        print(f"\n✅ {updated_count} loans are now available for repayments!")
        print("You can now:")
        print("1. View them in the Disbursed Loans page")
        print("2. Search for borrowers in the Record Repayment page")
        print("3. Record repayments for these loans")
    
    # Show current loan status distribution
    print(f"\n=== Current Loan Status Distribution ===")
    for status_code, status_name in LoanStatusChoices.choices:
        count = Loan.objects.filter(status=status_code).count()
        if count > 0:
            print(f"{status_name}: {count} loans")

if __name__ == '__main__':
    update_approved_loans()
