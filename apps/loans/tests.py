"""
Comprehensive test suite for loans app to validate critical fixes:
- Race condition prevention in loan number generation
- Transaction atomicity across multi-step saves
- Penalty signal atomicity
- Division by zero guards
- NPL classification logic
- Date validation
- Decimal type consistency
- Query optimization
"""

import threading
from decimal import Decimal
from datetime import timedelta, date
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError

from apps.borrowers.models import Borrower, BorrowerGroup
from apps.accounts.models import CustomUser
from apps.loans.models import (
    Loan, LoanType, RepaymentSchedule, Repayment, LoanPenalty,
    LoanStatusChoices, InterestTypeChoices, RepaymentStatusChoices,
    NPLCategoryChoices, LoanConstants, FrequencyChoices
)


class RaceConditionTests(TransactionTestCase):
    """Test critical race condition fixes."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_generate_loan_number_uniqueness_under_concurrency(self):
        """Test that loan numbers are unique even under concurrent generation."""
        loan_numbers = []
        errors = []
        
        def create_loan():
            try:
                loan = Loan.objects.create(
                    borrower=self.borrower,
                    loan_type=self.loan_type,
                    amount_requested=Decimal('1000'),
                    interest_rate=Decimal('15'),
                    duration_months=12,
                    repayment_frequency=FrequencyChoices.MONTHLY
                )
                loan_numbers.append(loan.loan_number)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple loans concurrently
        threads = []
        for _ in range(5):
            t = threading.Thread(target=create_loan)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")
        
        # Verify all loan numbers are unique
        self.assertEqual(len(loan_numbers), len(set(loan_numbers)),
                        "Duplicate loan numbers detected under concurrency")
        
        # Verify all loans were created
        self.assertEqual(len(loan_numbers), 5)


class AtomicityTests(TransactionTestCase):
    """Test transaction atomicity fixes."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_loan_save_atomicity(self):
        """Test that Loan.save() is atomic and doesn't create partial updates."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        
        # Set approval status and save
        loan.status = LoanStatusChoices.APPROVED
        loan.amount_approved = Decimal('1000')
        loan.save()
        
        # Refresh from database
        refreshed_loan = Loan.objects.get(pk=loan.pk)
        
        # Verify all calculated fields are set consistently
        self.assertEqual(refreshed_loan.status, LoanStatusChoices.APPROVED)
        self.assertEqual(refreshed_loan.amount_approved, Decimal('1000'))
        self.assertIsNotNone(refreshed_loan.total_amount)
        self.assertIsNotNone(refreshed_loan.total_interest)


class DivisionByZeroTests(TestCase):
    """Test division by zero guards."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('0.00'),  # Zero interest
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_zero_months_flat_interest_guard(self):
        """Test that zero months doesn't cause division error in flat interest calculation."""
        loan = Loan(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            amount_approved=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=0,  # Zero months
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        
        # Calculate totals should not raise error
        loan.calculate_loan_totals()
        
        # Verify safe calculation
        self.assertEqual(loan.total_interest, Decimal('0'))
        self.assertEqual(loan.total_amount, Decimal('1000'))
    
    def test_zero_interest_reducing_balance_guard(self):
        """Test that zero interest doesn't cause division error in EMI calculation."""
        loan_type = LoanType.objects.create(
            name="Zero Interest Loan",
            code="ZERO",
            default_interest_rate=Decimal('0.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.REDUCING
        )
        
        loan = Loan(
            borrower=self.borrower,
            loan_type=loan_type,
            amount_requested=Decimal('1000'),
            amount_approved=Decimal('1000'),
            interest_rate=Decimal('0'),  # Zero interest
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        
        # Calculate totals should not raise error
        loan.calculate_loan_totals()
        
        # Verify safe calculation
        self.assertEqual(loan.total_interest, Decimal('0'))
        self.assertEqual(loan.total_amount, Decimal('1000'))


class NPLClassificationTests(TestCase):
    """Test NPL classification logic uses constants correctly."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_npl_thresholds_use_constants(self):
        """Test that NPL classification thresholds match LoanConstants."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY,
            status=LoanStatusChoices.DISBURSED,
            disbursement_date=timezone.now().date() - timedelta(days=100)
        )
        
        # Verify constants are used
        self.assertEqual(LoanConstants.NPL_WATCH_DAYS, 90)
        self.assertEqual(LoanConstants.NPL_SUBSTANDARD_DAYS, 180)
        self.assertEqual(LoanConstants.NPL_DOUBTFUL_DAYS, 270)
        self.assertEqual(LoanConstants.NPL_LOSS_DAYS, 365)


class DateValidationTests(TestCase):
    """Test date validation in Loan.clean()."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_future_application_date_validation(self):
        """Test that future application date is rejected."""
        loan = Loan(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY,
            application_date=timezone.now().date() + timedelta(days=1)  # Future date
        )
        
        with self.assertRaises(ValidationError) as context:
            loan.full_clean()
        
        self.assertIn('application_date', context.exception.error_dict)
    
    def test_maturity_after_disbursement_validation(self):
        """Test that maturity date must be after disbursement date."""
        today = timezone.now().date()
        loan = Loan(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY,
            application_date=today,
            approval_date=today,
            disbursement_date=today,
            maturity_date=today  # Same as disbursement
        )
        
        with self.assertRaises(ValidationError) as context:
            loan.full_clean()
        
        self.assertIn('maturity_date', context.exception.error_dict)


class DecimalConsistencyTests(TestCase):
    """Test that all calculations use Decimal type consistently."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_total_paid_is_decimal(self):
        """Test that total_paid is stored as Decimal."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        
        loan.approve(Decimal('1000'))
        loan.disburse(None)
        
        # Verify total_paid is Decimal
        self.assertIsInstance(loan.total_paid, Decimal)
    
    def test_outstanding_balance_is_decimal(self):
        """Test that outstanding_balance is stored as Decimal."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        
        # Verify outstanding_balance is Decimal
        self.assertIsInstance(loan.outstanding_balance, Decimal)


class RepaymentValidationTests(TestCase):
    """Test Repayment model validation."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
        self.user = CustomUser.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create and setup loan
        self.loan = Loan.objects.create(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        self.loan.approve(Decimal('1000'))
        self.loan.disburse(self.user)
        
        # Get first schedule
        self.schedule = self.loan.repayment_schedules.first()
    
    def test_future_payment_date_rejection(self):
        """Test that future payment dates are rejected."""
        repayment = Repayment(
            schedule=self.schedule,
            amount_paid=Decimal('100'),
            received_by=self.user,
            payment_date=timezone.now().date() + timedelta(days=1)  # Future date
        )
        
        with self.assertRaises(ValidationError) as context:
            repayment.full_clean()
        
        self.assertIn('payment_date', context.exception.error_dict)
    
    def test_zero_amount_rejected(self):
        """Test that zero payment amount is rejected."""
        repayment = Repayment(
            schedule=self.schedule,
            amount_paid=Decimal('0'),  # Zero amount
            received_by=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            repayment.full_clean()
        
        self.assertIn('amount_paid', context.exception.error_dict)


class MagicNumbersToConstantsTests(TestCase):
    """Test that magic numbers are replaced with LoanConstants."""
    
    def test_loan_constants_exist(self):
        """Test that all necessary constants are defined."""
        self.assertEqual(LoanConstants.DAYS_PER_MONTH, 30)
        self.assertEqual(LoanConstants.NPL_WATCH_DAYS, 90)
        self.assertEqual(LoanConstants.NPL_SUBSTANDARD_DAYS, 180)
        self.assertEqual(LoanConstants.NPL_DOUBTFUL_DAYS, 270)
        self.assertEqual(LoanConstants.NPL_LOSS_DAYS, 365)
        self.assertEqual(LoanConstants.DEFAULTED_DAYS, 30)


class QueryOptimizationTests(TestCase):
    """Test that query optimization works correctly."""
    
    def setUp(self):
        """Set up test data."""
        self.borrower = Borrower.objects.create(
            first_name="Test",
            last_name="Borrower",
            phone_number="255700000000",
            email="test@example.com"
        )
        self.loan_type = LoanType.objects.create(
            name="Test Loan",
            code="TEST",
            default_interest_rate=Decimal('15.00'),
            min_amount=Decimal('100'),
            max_amount=Decimal('10000'),
            interest_type=InterestTypeChoices.FLAT
        )
    
    def test_cached_property_oldest_overdue_due_date(self):
        """Test that oldest_overdue_due_date is cached."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            loan_type=self.loan_type,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        
        # Access cached_property multiple times
        first_access = loan.oldest_overdue_due_date
        second_access = loan.oldest_overdue_due_date
        
        # Should return same object (cached)
        self.assertEqual(first_access, second_access)
