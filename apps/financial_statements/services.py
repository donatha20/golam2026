"""
Financial statement generation services.
"""
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime
from collections import defaultdict, OrderedDict

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from .models import AccountingPeriod, AccountClassification, FinancialStatementRun


class FinancialStatementService:
    """Core service for generating financial statements."""
    
    def __init__(self, period=None, comparison_period=None):
        self.period = period
        self.comparison_period = comparison_period
        self.accounts = Account.objects.filter(is_active=True).order_by('account_code')
    
    def get_account_balance(self, account, as_of_date=None, period=None):
        """
        Calculate account balance as of a specific date or for a period.
        """
        if period:
            # Balance for a specific period
            entries = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__is_posted=True,
                journal_entry__entry_date__gte=period.start_date,
                journal_entry__entry_date__lte=period.end_date
            )
        elif as_of_date:
            # Balance as of a specific date
            entries = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__is_posted=True,
                journal_entry__entry_date__lte=as_of_date
            )
        else:
            # All-time balance
            entries = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__is_posted=True
            )
        
        total_debits = entries.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')
        total_credits = entries.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')
        
        # Calculate balance based on account type
        if account.account_type in ['asset', 'expense']:
            # Normal debit balance
            balance = total_debits - total_credits
        else:
            # Normal credit balance (liability, equity, revenue)
            balance = total_credits - total_debits
        
        return balance
    
    def get_trial_balance_data(self):
        """Generate trial balance data."""
        trial_balance = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        for account in self.accounts:
            balance = self.get_account_balance(account, as_of_date=self.period.end_date)
            
            if balance != 0:  # Only include accounts with balances
                if account.account_type in ['asset', 'expense']:
                    # Debit balance accounts
                    debit_balance = balance if balance > 0 else Decimal('0.00')
                    credit_balance = abs(balance) if balance < 0 else Decimal('0.00')
                else:
                    # Credit balance accounts
                    debit_balance = abs(balance) if balance < 0 else Decimal('0.00')
                    credit_balance = balance if balance > 0 else Decimal('0.00')
                
                trial_balance.append({
                    'account_code': account.account_code,
                    'account_name': account.account_name,
                    'account_type': account.account_type,
                    'debit_balance': debit_balance,
                    'credit_balance': credit_balance,
                    'balance': balance
                })
                
                total_debits += debit_balance
                total_credits += credit_balance
        
        return {
            'accounts': trial_balance,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': total_debits == total_credits,
            'period': self.period,
            'generated_at': timezone.now()
        }
    
    def get_balance_sheet_data(self):
        """Generate balance sheet data."""
        balance_sheet = {
            'assets': {
                'current_assets': [],
                'non_current_assets': [],
                'total_assets': Decimal('0.00')
            },
            'liabilities': {
                'current_liabilities': [],
                'non_current_liabilities': [],
                'total_liabilities': Decimal('0.00')
            },
            'equity': {
                'equity_accounts': [],
                'total_equity': Decimal('0.00')
            },
            'period': self.period,
            'comparison_period': self.comparison_period,
            'generated_at': timezone.now()
        }
        
        # Get classified accounts
        classified_accounts = AccountClassification.objects.select_related('account').all()
        classification_map = {ac.account_id: ac for ac in classified_accounts}
        
        for account in self.accounts.filter(account_type__in=['asset', 'liability', 'equity']):
            balance = self.get_account_balance(account, as_of_date=self.period.end_date)
            
            if balance != 0:
                account_data = {
                    'account_code': account.account_code,
                    'account_name': account.account_name,
                    'balance': balance,
                    'comparison_balance': None
                }
                
                # Add comparison period balance if available
                if self.comparison_period:
                    account_data['comparison_balance'] = self.get_account_balance(
                        account, as_of_date=self.comparison_period.end_date
                    )
                
                # Classify account
                classification = classification_map.get(account.id)
                
                if account.account_type == 'asset':
                    if classification and classification.classification_type == 'current_assets':
                        balance_sheet['assets']['current_assets'].append(account_data)
                    else:
                        balance_sheet['assets']['non_current_assets'].append(account_data)
                    balance_sheet['assets']['total_assets'] += balance
                
                elif account.account_type == 'liability':
                    if classification and classification.classification_type == 'current_liabilities':
                        balance_sheet['liabilities']['current_liabilities'].append(account_data)
                    else:
                        balance_sheet['liabilities']['non_current_liabilities'].append(account_data)
                    balance_sheet['liabilities']['total_liabilities'] += balance
                
                elif account.account_type == 'equity':
                    balance_sheet['equity']['equity_accounts'].append(account_data)
                    balance_sheet['equity']['total_equity'] += balance
        
        # Calculate totals
        balance_sheet['total_liabilities_and_equity'] = (
            balance_sheet['liabilities']['total_liabilities'] + 
            balance_sheet['equity']['total_equity']
        )
        
        balance_sheet['is_balanced'] = (
            balance_sheet['assets']['total_assets'] == 
            balance_sheet['total_liabilities_and_equity']
        )
        
        return balance_sheet
    
    def get_income_statement_data(self):
        """Generate income statement data."""
        income_statement = {
            'revenue': {
                'operating_revenue': [],
                'non_operating_revenue': [],
                'total_revenue': Decimal('0.00')
            },
            'expenses': {
                'operating_expenses': [],
                'non_operating_expenses': [],
                'total_expenses': Decimal('0.00')
            },
            'net_income': Decimal('0.00'),
            'period': self.period,
            'comparison_period': self.comparison_period,
            'generated_at': timezone.now()
        }
        
        # Get classified accounts
        classified_accounts = AccountClassification.objects.select_related('account').all()
        classification_map = {ac.account_id: ac for ac in classified_accounts}
        
        for account in self.accounts.filter(account_type__in=['revenue', 'expense']):
            balance = self.get_account_balance(account, period=self.period)
            
            if balance != 0:
                account_data = {
                    'account_code': account.account_code,
                    'account_name': account.account_name,
                    'balance': balance,
                    'comparison_balance': None
                }
                
                # Add comparison period balance if available
                if self.comparison_period:
                    account_data['comparison_balance'] = self.get_account_balance(
                        account, period=self.comparison_period
                    )
                
                # Classify account
                classification = classification_map.get(account.id)
                
                if account.account_type == 'revenue':
                    if classification and classification.classification_type == 'operating_revenue':
                        income_statement['revenue']['operating_revenue'].append(account_data)
                    else:
                        income_statement['revenue']['non_operating_revenue'].append(account_data)
                    income_statement['revenue']['total_revenue'] += balance
                
                elif account.account_type == 'expense':
                    if classification and classification.classification_type == 'operating_expenses':
                        income_statement['expenses']['operating_expenses'].append(account_data)
                    else:
                        income_statement['expenses']['non_operating_expenses'].append(account_data)
                    income_statement['expenses']['total_expenses'] += balance
        
        # Calculate net income
        income_statement['net_income'] = (
            income_statement['revenue']['total_revenue'] - 
            income_statement['expenses']['total_expenses']
        )
        
        return income_statement
    
    def get_cash_flow_data(self):
        """Generate cash flow statement data using indirect method."""
        cash_flow = {
            'operating_activities': {
                'net_income': Decimal('0.00'),
                'adjustments': [],
                'working_capital_changes': [],
                'net_cash_from_operations': Decimal('0.00')
            },
            'investing_activities': {
                'activities': [],
                'net_cash_from_investing': Decimal('0.00')
            },
            'financing_activities': {
                'activities': [],
                'net_cash_from_financing': Decimal('0.00')
            },
            'net_change_in_cash': Decimal('0.00'),
            'cash_beginning': Decimal('0.00'),
            'cash_ending': Decimal('0.00'),
            'period': self.period,
            'generated_at': timezone.now()
        }
        
        # Start with net income from income statement
        income_data = self.get_income_statement_data()
        cash_flow['operating_activities']['net_income'] = income_data['net_income']
        
        # Get cash accounts
        cash_accounts = self.accounts.filter(
            Q(account_name__icontains='cash') | Q(account_code__startswith='1001')
        )
        
        # Calculate cash balances
        for account in cash_accounts:
            ending_balance = self.get_account_balance(account, as_of_date=self.period.end_date)
            beginning_balance = self.get_account_balance(account, as_of_date=self.period.start_date)
            
            cash_flow['cash_ending'] += ending_balance
            cash_flow['cash_beginning'] += beginning_balance
        
        cash_flow['net_change_in_cash'] = cash_flow['cash_ending'] - cash_flow['cash_beginning']
        
        # TODO: Implement detailed cash flow analysis
        # This would require more sophisticated analysis of account changes
        # and classification of activities as operating, investing, or financing
        
        return cash_flow


class FinancialStatementGenerator:
    """High-level service for generating and managing financial statements."""
    
    @staticmethod
    def generate_trial_balance(period, user=None):
        """Generate trial balance for a period."""
        service = FinancialStatementService(period=period)
        data = service.get_trial_balance_data()
        
        # Create statement run record
        run = FinancialStatementRun.objects.create(
            statement_type='trial_balance',
            period=period,
            status='completed',
            results=data,
            created_by=user,
            completed_at=timezone.now()
        )
        
        return run, data
    
    @staticmethod
    def generate_balance_sheet(period, comparison_period=None, user=None):
        """Generate balance sheet for a period."""
        service = FinancialStatementService(period=period, comparison_period=comparison_period)
        data = service.get_balance_sheet_data()
        
        # Create statement run record
        run = FinancialStatementRun.objects.create(
            statement_type='balance_sheet',
            period=period,
            comparison_period=comparison_period,
            status='completed',
            results=data,
            created_by=user,
            completed_at=timezone.now()
        )
        
        return run, data
    
    @staticmethod
    def generate_income_statement(period, comparison_period=None, user=None):
        """Generate income statement for a period."""
        service = FinancialStatementService(period=period, comparison_period=comparison_period)
        data = service.get_income_statement_data()
        
        # Create statement run record
        run = FinancialStatementRun.objects.create(
            statement_type='income_statement',
            period=period,
            comparison_period=comparison_period,
            status='completed',
            results=data,
            created_by=user,
            completed_at=timezone.now()
        )
        
        return run, data
    
    @staticmethod
    def generate_cash_flow_statement(period, user=None):
        """Generate cash flow statement for a period."""
        service = FinancialStatementService(period=period)
        data = service.get_cash_flow_data()
        
        # Create statement run record
        run = FinancialStatementRun.objects.create(
            statement_type='cash_flow',
            period=period,
            status='completed',
            results=data,
            created_by=user,
            completed_at=timezone.now()
        )
        
        return run, data
    
    @staticmethod
    def generate_complete_financial_statements(period, comparison_period=None, user=None):
        """Generate complete set of financial statements."""
        service = FinancialStatementService(period=period, comparison_period=comparison_period)
        
        complete_data = {
            'trial_balance': service.get_trial_balance_data(),
            'balance_sheet': service.get_balance_sheet_data(),
            'income_statement': service.get_income_statement_data(),
            'cash_flow': service.get_cash_flow_data(),
            'generated_at': timezone.now()
        }
        
        # Create statement run record
        run = FinancialStatementRun.objects.create(
            statement_type='complete_set',
            period=period,
            comparison_period=comparison_period,
            status='completed',
            results=complete_data,
            created_by=user,
            completed_at=timezone.now()
        )
        
        return run, complete_data
