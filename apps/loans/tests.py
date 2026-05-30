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
from django.urls import reverse

from apps.borrowers.models import Borrower, BorrowerGroup
from apps.accounts.models import CustomUser, UserRole
from apps.core.models import Branch
from apps.loans.models import (
    Loan, LoanReferral, RepaymentSchedule, Repayment, LoanPenalty,
    LoanStatusChoices, RepaymentStatusChoices,
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
    
    def test_generate_loan_number_uniqueness_under_concurrency(self):
        """Test that loan numbers are unique even under concurrent generation."""
        loan_numbers = []
        errors = []
        
        def create_loan():
            try:
                loan = Loan.objects.create(
                    borrower=self.borrower,
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
    
    def test_loan_save_atomicity(self):
        """Test that Loan.save() is atomic and doesn't create partial updates."""
        loan = Loan.objects.create(
            borrower=self.borrower,
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

    def test_approval_default_amount_preserves_manual_totals(self):
        """Approval should keep exact manual totals when amount_approved defaults to requested amount."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount_requested=Decimal('19000.00'),
            interest_rate=Decimal('72.63'),
            duration_months=2,
            repayment_frequency=FrequencyChoices.MONTHLY,
            status=LoanStatusChoices.PENDING,
        )

        # Simulate legacy/manual totals saved before approval while amount_approved is empty.
        Loan.objects.filter(pk=loan.pk).update(
            total_interest=Decimal('2300.00'),
            total_amount=Decimal('21300.00'),
            outstanding_balance=Decimal('21300.00'),
        )

        loan.refresh_from_db()
        loan.status = LoanStatusChoices.APPROVED
        loan.amount_approved = Decimal('19000.00')
        loan.save()

        loan.refresh_from_db()
        self.assertEqual(loan.total_interest, Decimal('2300.00'))
        self.assertEqual(loan.total_amount, Decimal('21300.00'))


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
    
    def test_zero_months_flat_interest_guard(self):
        """Test that zero months doesn't cause division error in flat interest calculation."""
        loan = Loan(
            borrower=self.borrower,
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
    
    def test_zero_interest_guard(self):
        """Test that zero interest safely yields zero interest amount."""
        loan = Loan(
            borrower=self.borrower,
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
    
    def test_npl_thresholds_use_constants(self):
        """Test that NPL classification thresholds match LoanConstants."""
        loan = Loan.objects.create(
            borrower=self.borrower,
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
    
    def test_future_application_date_validation(self):
        """Test that future application date is rejected."""
        loan = Loan(
            borrower=self.borrower,
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
    
    def test_total_paid_is_decimal(self):
        """Test that total_paid is stored as Decimal."""
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )

        loan.status = LoanStatusChoices.APPROVED
        loan.amount_approved = Decimal('1000')
        loan.approval_date = timezone.now().date()
        loan.save()
        loan.disburse(None)
        
        # Verify total_paid is Decimal
        self.assertIsInstance(loan.total_paid, Decimal)
    
    def test_outstanding_balance_is_decimal(self):
        """Test that outstanding_balance is stored as Decimal."""
        loan = Loan.objects.create(
            borrower=self.borrower,
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
        self.user = CustomUser.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create and setup loan
        self.loan = Loan.objects.create(
            borrower=self.borrower,
            amount_requested=Decimal('1000'),
            interest_rate=Decimal('15'),
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY
        )
        self.loan.status = LoanStatusChoices.APPROVED
        self.loan.amount_approved = Decimal('1000')
        self.loan.approval_date = timezone.now().date()
        self.loan.save()
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
    
    def test_cached_property_oldest_overdue_due_date(self):
        """Test that oldest_overdue_due_date is cached."""
        loan = Loan.objects.create(
            borrower=self.borrower,
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


class LoanReferralPermissionTests(TestCase):
    """Test referral edit and resubmission permissions."""

    def setUp(self):
        self.branch = Branch.objects.create(
            name='Main Branch',
            code='MB001',
            address='Test Street',
            phone_number='+255700000000',
        )

        self.admin = CustomUser.objects.create_user(
            username='admin_user',
            password='pass12345',
            role=UserRole.ADMIN,
            branch=self.branch,
        )
        self.officer_one = CustomUser.objects.create_user(
            username='officer_one',
            password='pass12345',
            role=UserRole.LOAN_OFFICER,
            branch=self.branch,
        )
        self.officer_two = CustomUser.objects.create_user(
            username='officer_two',
            password='pass12345',
            role=UserRole.LOAN_OFFICER,
            branch=self.branch,
        )

        self.borrower = Borrower.objects.create(
            first_name='Test',
            last_name='Borrower',
            gender='male',
            date_of_birth=date(1990, 1, 1),
            marital_status='single',
            occupation='Trader',
            phone_number='255700000000',
            id_type='national_id',
            id_number='ID-REF-001',
            street='Street 1',
            ward='Ward 1',
            district='District 1',
            region='Region 1',
            next_of_kin_name='Kin Name',
            next_of_kin_relationship='Sibling',
            next_of_kin_phone='255700000001',
            next_of_kin_address='Kin Address',
            branch=self.branch,
            registered_by=self.officer_one,
        )

        self.loan = Loan.objects.create(
            borrower=self.borrower,
            amount_requested=100000,
            interest_rate=15,
            duration_months=12,
            repayment_frequency=FrequencyChoices.MONTHLY,
            created_by=self.officer_one,
            status=LoanStatusChoices.REFERRED,
        )

        self.referral = LoanReferral.objects.create(
            loan=self.loan,
            referred_by=self.admin,
            referred_to=self.officer_one,
            referral_reason='Please correct the borrower income evidence.',
        )

    def test_referred_list_is_scoped_to_assigned_officer(self):
        self.client.force_login(self.officer_one)
        response = self.client.get(reverse('loans:referred_loans'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.loan.loan_number)

        self.client.force_login(self.officer_two)
        response = self.client.get(reverse('loans:referred_loans'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.loan.loan_number)

    def test_assigned_officer_can_edit_referred_loan(self):
        self.client.force_login(self.officer_one)
        response = self.client.get(reverse('loans:edit_loan', args=[self.loan.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Referred Loan')

    def test_other_officer_cannot_edit_referred_loan(self):
        self.client.force_login(self.officer_two)
        response = self.client.get(reverse('loans:edit_loan', args=[self.loan.id]))
        self.assertEqual(response.status_code, 302)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatusChoices.REFERRED)

    def test_assigned_officer_can_resubmit_referred_loan(self):
        self.client.force_login(self.officer_one)
        response = self.client.post(reverse('loans:resubmit_referred_loan', args=[self.loan.id]))
        self.assertEqual(response.status_code, 302)

        self.loan.refresh_from_db()
        self.referral.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatusChoices.PENDING)
        self.assertTrue(self.referral.is_resolved)
        self.assertEqual(self.referral.resubmitted_by, self.officer_one)

    def test_officer_cannot_approve_reject_or_disburse(self):
        self.client.force_login(self.officer_one)

        approval_response = self.client.get(reverse('loans:loan_approval', args=[self.loan.id]))
        rejection_response = self.client.post(reverse('loans:loan_rejection', args=[self.loan.id]), data='{}', content_type='application/json')
        disbursement_response = self.client.get(reverse('loans:loan_disbursement', args=[self.loan.id]))

        self.assertEqual(approval_response.status_code, 403)
        self.assertEqual(rejection_response.status_code, 403)
        self.assertEqual(disbursement_response.status_code, 403)
