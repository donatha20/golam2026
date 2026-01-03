"""
Pytest configuration and fixtures for the microfinance system.
"""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from decimal import Decimal
import factory
from factory.django import DjangoModelFactory

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up test database."""
    with django_db_blocker.unblock():
        call_command('migrate', '--run-syncdb')


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def admin_user(db):
    """Create admin user."""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def staff_user(db):
    """Create staff user."""
    return User.objects.create_user(
        username='staff',
        email='staff@test.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def regular_user(db):
    """Create regular user."""
    return User.objects.create_user(
        username='user',
        email='user@test.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, regular_user):
    """Client with authenticated user."""
    client.force_login(regular_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Client with admin user."""
    client.force_login(admin_user)
    return client


# Model Factories
class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True


class BorrowerFactory(DjangoModelFactory):
    class Meta:
        model = 'borrowers.Borrower'
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone_number = factory.Faker('phone_number')
    email = factory.Faker('email')
    national_id = factory.Sequence(lambda n: f'ID{n:08d}')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=80)
    gender = factory.Iterator(['male', 'female'])
    status = 'active'
    created_by = factory.SubFactory(UserFactory)


class LoanTypeFactory(DjangoModelFactory):
    class Meta:
        model = 'loans.LoanType'
    
    name = factory.Faker('word')
    description = factory.Faker('text')
    interest_rate = Decimal('15.00')
    max_amount = Decimal('100000.00')
    min_amount = Decimal('1000.00')
    max_duration_months = 24
    min_duration_months = 6
    created_by = factory.SubFactory(UserFactory)


class LoanFactory(DjangoModelFactory):
    class Meta:
        model = 'loans.Loan'
    
    loan_number = factory.Sequence(lambda n: f'LN{n:08d}')
    borrower = factory.SubFactory(BorrowerFactory)
    loan_type = factory.SubFactory(LoanTypeFactory)
    amount_requested = Decimal('50000.00')
    amount_approved = Decimal('50000.00')
    interest_rate = Decimal('15.00')
    duration_months = 12
    purpose = factory.Faker('text')
    status = 'pending'
    created_by = factory.SubFactory(UserFactory)


class SavingsAccountFactory(DjangoModelFactory):
    class Meta:
        model = 'savings.SavingsAccount'
    
    account_number = factory.Sequence(lambda n: f'SA{n:08d}')
    borrower = factory.SubFactory(BorrowerFactory)
    balance = Decimal('1000.00')
    interest_rate = Decimal('5.00')
    status = 'active'
    created_by = factory.SubFactory(UserFactory)


@pytest.fixture
def borrower(db):
    """Create test borrower."""
    return BorrowerFactory()


@pytest.fixture
def loan_type(db):
    """Create test loan type."""
    return LoanTypeFactory()


@pytest.fixture
def loan(db, borrower, loan_type):
    """Create test loan."""
    return LoanFactory(borrower=borrower, loan_type=loan_type)


@pytest.fixture
def savings_account(db, borrower):
    """Create test savings account."""
    return SavingsAccountFactory(borrower=borrower)


@pytest.fixture
def sample_data(db):
    """Create sample data for testing."""
    # Create users
    admin = UserFactory(username='admin', is_staff=True, is_superuser=True)
    staff = UserFactory(username='staff', is_staff=True)
    
    # Create borrowers
    borrowers = BorrowerFactory.create_batch(5, created_by=staff)
    
    # Create loan types
    loan_types = LoanTypeFactory.create_batch(3, created_by=admin)
    
    # Create loans
    loans = []
    for borrower in borrowers:
        loan = LoanFactory(
            borrower=borrower,
            loan_type=loan_types[0],
            created_by=staff
        )
        loans.append(loan)
    
    # Create savings accounts
    savings = []
    for borrower in borrowers:
        account = SavingsAccountFactory(
            borrower=borrower,
            created_by=staff
        )
        savings.append(account)
    
    return {
        'admin': admin,
        'staff': staff,
        'borrowers': borrowers,
        'loan_types': loan_types,
        'loans': loans,
        'savings': savings,
    }


@pytest.fixture
def mock_sms_service(monkeypatch):
    """Mock SMS service for testing."""
    def mock_send_sms(phone_number, message):
        return {'success': True, 'message_id': 'test123'}
    
    monkeypatch.setattr('apps.core.utils.sms.send_sms', mock_send_sms)


@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service for testing."""
    def mock_send_mail(*args, **kwargs):
        return True
    
    monkeypatch.setattr('django.core.mail.send_mail', mock_send_mail)


@pytest.fixture
def performance_test_data(db):
    """Create large dataset for performance testing."""
    # Create many borrowers for performance testing
    borrowers = BorrowerFactory.create_batch(100)
    
    # Create loans for performance testing
    loan_type = LoanTypeFactory()
    loans = []
    for borrower in borrowers:
        loan = LoanFactory(borrower=borrower, loan_type=loan_type)
        loans.append(loan)
    
    return {
        'borrowers': borrowers,
        'loans': loans,
        'loan_type': loan_type,
    }


# Custom markers for different test types
pytestmark = [
    pytest.mark.django_db,
]
