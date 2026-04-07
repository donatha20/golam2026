"""
Service functions for finance tracker accounting integration.
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from .models import Income, Expenditure


class AccountingService:
    """Service class for handling accounting integration."""
    
    @staticmethod
    def get_or_create_default_accounts():
        """Get or create default accounts for income and expenditure tracking."""
        
        # Cash account (Asset)
        cash_account, created = Account.objects.get_or_create(
            account_code='1001',
            defaults={
                'account_name': 'Cash in Hand',
                'account_type': 'asset',
                'description': 'Cash available for operations'
            }
        )
        
        # Bank account (Asset)
        bank_account, created = Account.objects.get_or_create(
            account_code='1002',
            defaults={
                'account_name': 'Bank Account',
                'account_type': 'asset',
                'description': 'Main operating bank account'
            }
        )
        
        # Income account (Revenue)
        income_account, created = Account.objects.get_or_create(
            account_code='4001',
            defaults={
                'account_name': 'General Income',
                'account_type': 'revenue',
                'description': 'General income and revenue'
            }
        )
        
        # Expenditure account (Expense)
        expense_account, created = Account.objects.get_or_create(
            account_code='5001',
            defaults={
                'account_name': 'General Expenses',
                'account_type': 'expense',
                'description': 'General operational expenses'
            }
        )
        
        return {
            'cash': cash_account,
            'bank': bank_account,
            'income': income_account,
            'expense': expense_account
        }
    
    @staticmethod
    def generate_journal_entry_number():
        """Generate unique journal entry number."""
        last_entry = JournalEntry.objects.filter(
            entry_number__startswith='JE'
        ).order_by('entry_number').last()
        
        if last_entry:
            last_number = int(last_entry.entry_number[2:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"JE{new_number:06d}"
    
    @classmethod
    @transaction.atomic
    def record_income_transaction(cls, income_instance, user=None):
        """
        Create journal entry for income recording.
        
        Journal Entry:
        Dr. Cash/Bank Account    [Amount]
        Cr. Income Account                [Amount]
        """
        accounts = cls.get_or_create_default_accounts()
        
        # Determine which asset account to use based on payment method
        payment_method = (income_instance.payment_method or '').lower()
        if 'bank' in payment_method or 'transfer' in payment_method or 'cheque' in payment_method:
            asset_account = accounts['bank']
        else:
            asset_account = accounts['cash']
        
        # Create journal entry
        journal_entry = JournalEntry.objects.create(
            entry_number=cls.generate_journal_entry_number(),
            entry_date=income_instance.income_date,
            description=f"Income recorded: {income_instance.get_source_display()} - {income_instance.description[:100]}",
            reference_type='Income',
            reference_id=income_instance.id,
            is_posted=True
        )
        
        # Create journal entry lines
        # Debit: Cash/Bank (Asset increases)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=asset_account,
            debit_amount=income_instance.amount,
            credit_amount=Decimal('0.00'),
            description=f"Income received from {income_instance.received_from or 'various sources'}"
        )
        
        # Credit: Income (Revenue increases)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=accounts['income'],
            debit_amount=Decimal('0.00'),
            credit_amount=income_instance.amount,
            description=f"{income_instance.get_source_display()}: {income_instance.description[:100]}"
        )
        
        return journal_entry
    
    @classmethod
    @transaction.atomic
    def record_expenditure_transaction(cls, expenditure_instance, user=None):
        """
        Create journal entry for expenditure recording.
        
        Journal Entry:
        Dr. Expense Account      [Amount]
        Cr. Cash/Bank Account             [Amount]
        """
        accounts = cls.get_or_create_default_accounts()
        
        # Determine which asset account to use based on payment method
        payment_method = (expenditure_instance.payment_method or '').lower()
        if 'bank' in payment_method or 'transfer' in payment_method or 'cheque' in payment_method:
            asset_account = accounts['bank']
        else:
            asset_account = accounts['cash']
        
        # Create journal entry
        journal_entry = JournalEntry.objects.create(
            entry_number=cls.generate_journal_entry_number(),
            entry_date=expenditure_instance.expenditure_date,
            description=f"Expenditure: {expenditure_instance.get_expenditure_type_display()} - {expenditure_instance.description[:100]}",
            reference_type='Expenditure',
            reference_id=expenditure_instance.id,
            is_posted=True
        )
        
        # Create journal entry lines
        # Debit: Expense (Expense increases)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=accounts['expense'],
            debit_amount=expenditure_instance.amount,
            credit_amount=Decimal('0.00'),
            description=f"{expenditure_instance.get_expenditure_type_display()}: {expenditure_instance.description[:100]}"
        )
        
        # Credit: Cash/Bank (Asset decreases)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=asset_account,
            debit_amount=Decimal('0.00'),
            credit_amount=expenditure_instance.amount,
            description=f"Payment to {expenditure_instance.vendor_name}"
        )
        
        return journal_entry
    
    @classmethod
    def get_account_balance(cls, account_code):
        """Get current balance for an account."""
        try:
            account = Account.objects.get(account_code=account_code)
            
            # Get all journal entry lines for this account
            lines = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__is_posted=True
            )
            
            total_debits = sum(line.debit_amount for line in lines)
            total_credits = sum(line.credit_amount for line in lines)
            
            # Calculate balance based on account type
            if account.account_type in ['asset', 'expense']:
                # Normal debit balance
                balance = total_debits - total_credits
            else:
                # Normal credit balance (liability, equity, revenue)
                balance = total_credits - total_debits
            
            return balance
            
        except Account.DoesNotExist:
            return Decimal('0.00')
    
    @classmethod
    def get_cash_balance(cls):
        """Get current cash balance."""
        return cls.get_account_balance('1001')
    
    @classmethod
    def get_bank_balance(cls):
        """Get current bank balance."""
        return cls.get_account_balance('1002')
    
    @classmethod
    def get_total_liquid_assets(cls):
        """Get total liquid assets (cash + bank)."""
        return cls.get_cash_balance() + cls.get_bank_balance()
    
    @classmethod
    def get_financial_summary(cls):
        """Get summary of financial position."""
        accounts = cls.get_or_create_default_accounts()
        
        return {
            'cash_balance': cls.get_cash_balance(),
            'bank_balance': cls.get_bank_balance(),
            'total_liquid_assets': cls.get_total_liquid_assets(),
            'total_income': cls.get_account_balance('4001'),
            'total_expenses': cls.get_account_balance('5001'),
            'net_income': cls.get_account_balance('4001') - cls.get_account_balance('5001')
        }


def create_income_journal_entry(income_instance, user=None):
    """
    Helper function to create journal entry when income is recorded.
    This can be called from signals or views.
    """
    try:
        return AccountingService.record_income_transaction(income_instance, user)
    except Exception as e:
        # Log the error but don't fail the income creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create journal entry for income {income_instance.income_id}: {str(e)}")
        return None


def create_expenditure_journal_entry(expenditure_instance, user=None):
    """
    Helper function to create journal entry when expenditure is recorded.
    This can be called from signals or views.
    """
    try:
        return AccountingService.record_expenditure_transaction(expenditure_instance, user)
    except Exception as e:
        # Log the error but don't fail the expenditure creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create journal entry for expenditure {expenditure_instance.expenditure_id}: {str(e)}")
        return None


def get_account_balances():
    """Get current account balances for dashboard display."""
    return AccountingService.get_financial_summary()


