"""
Django signals for automatic savings account creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from apps.borrowers.models import Borrower
from .models import SavingsAccount, SavingsProduct


@receiver(post_save, sender=Borrower)
def create_savings_account_for_borrower(sender, instance, created, **kwargs):
    """
    Automatically create a savings account when a new borrower is registered.
    """
    if created:  # Only for newly created borrowers
        try:
            # Get the default savings product
            default_product = get_default_savings_product()
            
            if default_product:
                # Create savings account for the new borrower
                savings_account = SavingsAccount.objects.create(
                    borrower=instance,
                    savings_product=default_product,
                    opened_date=instance.registration_date or timezone.now().date(),
                    opened_by=instance.registered_by,
                    status='active',
                    balance=Decimal('0.00'),
                    available_balance=Decimal('0.00'),
                    created_by=instance.registered_by,
                )
                
                print(f"✅ Savings account {savings_account.account_number} automatically created for borrower {instance.get_full_name()}")
                
        except Exception as e:
            print(f"❌ Error creating savings account for borrower {instance.get_full_name()}: {str(e)}")


def get_default_savings_product():
    """
    Get the default savings product for new accounts.
    Returns the first active savings product or creates a basic one if none exists.
    """
    try:
        # Try to get an existing active savings product
        default_product = SavingsProduct.objects.filter(is_active=True).first()
        
        if not default_product:
            # Create a basic default savings product if none exists
            default_product = SavingsProduct.objects.create(
                name="Basic Savings Account",
                description="Default savings account for all clients",
                interest_rate=Decimal('2.00'),  # 2% annual interest
                interest_calculation_method='simple',
                interest_posting_frequency='monthly',
                minimum_opening_balance=Decimal('50.00'),
                minimum_balance=Decimal('25.00'),
                minimum_deposit=Decimal('10.00'),
                minimum_withdrawal=Decimal('10.00'),
                account_maintenance_fee=Decimal('0.00'),
                withdrawal_fee=Decimal('0.00'),
                is_active=True,
                requires_approval=False,
                allow_overdraft=False,
            )
            print(f"✅ Default savings product '{default_product.name}' created")
            
        return default_product
        
    except Exception as e:
        print(f"❌ Error getting/creating default savings product: {str(e)}")
        return None


