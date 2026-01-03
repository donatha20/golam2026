"""
System integration tests for the microfinance system.
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


@pytest.mark.integration
class TestSystemIntegration:
    """Test complete system workflows."""
    
    def test_complete_loan_workflow(self, admin_client, sample_data):
        """Test complete loan workflow from application to disbursement."""
        borrower = sample_data['borrowers'][0]
        loan_type = sample_data['loan_types'][0]
        
        # 1. Create loan application
        loan_data = {
            'borrower': borrower.id,
            'loan_type': loan_type.id,
            'amount_requested': '50000.00',
            'duration_months': 12,
            'purpose': 'Business expansion',
        }
        
        response = admin_client.post(reverse('loans:add_loan'), loan_data)
        assert response.status_code in [200, 302]
        
        # 2. Verify loan was created
        from apps.loans.models import Loan
        loan = Loan.objects.filter(borrower=borrower).first()
        assert loan is not None
        assert loan.status == 'pending'
        
        # 3. Approve loan
        approval_data = {
            'amount_approved': '45000.00',
            'interest_rate': '15.00',
            'approval_notes': 'Approved with conditions',
        }
        
        response = admin_client.post(
            reverse('loans:loan_approval', args=[loan.id]),
            approval_data
        )
        assert response.status_code in [200, 302]
        
        # 4. Verify loan approval
        loan.refresh_from_db()
        assert loan.status == 'approved'
        assert loan.amount_approved == Decimal('45000.00')
        
        # 5. Disburse loan
        disbursement_data = {
            'disbursement_method': 'bank_transfer',
            'disbursement_notes': 'Disbursed to borrower account',
        }
        
        response = admin_client.post(
            reverse('loans:loan_disbursement', args=[loan.id]),
            disbursement_data
        )
        assert response.status_code in [200, 302]
        
        # 6. Verify loan disbursement
        loan.refresh_from_db()
        assert loan.status == 'disbursed'
        assert loan.disbursement_date is not None
        
        # 7. Verify repayment schedule was created
        assert loan.repayment_schedules.count() > 0
    
    def test_savings_account_workflow(self, admin_client, sample_data):
        """Test savings account creation and transactions."""
        borrower = sample_data['borrowers'][0]
        
        # 1. Create savings account
        account_data = {
            'borrower': borrower.id,
            'account_type': 'regular',
            'initial_deposit': '1000.00',
            'interest_rate': '5.00',
        }
        
        response = admin_client.post(reverse('savings:add_account'), account_data)
        assert response.status_code in [200, 302]
        
        # 2. Verify account creation
        from apps.savings.models import SavingsAccount
        account = SavingsAccount.objects.filter(borrower=borrower).first()
        assert account is not None
        assert account.balance == Decimal('1000.00')
        
        # 3. Make deposit
        deposit_data = {
            'account': account.id,
            'amount': '500.00',
            'transaction_type': 'deposit',
            'description': 'Cash deposit',
        }
        
        response = admin_client.post(reverse('savings:deposit'), deposit_data)
        assert response.status_code in [200, 302]
        
        # 4. Verify deposit
        account.refresh_from_db()
        assert account.balance == Decimal('1500.00')
        
        # 5. Make withdrawal
        withdrawal_data = {
            'account': account.id,
            'amount': '200.00',
            'transaction_type': 'withdrawal',
            'description': 'Cash withdrawal',
        }
        
        response = admin_client.post(reverse('savings:withdraw'), withdrawal_data)
        assert response.status_code in [200, 302]
        
        # 6. Verify withdrawal
        account.refresh_from_db()
        assert account.balance == Decimal('1300.00')
    
    def test_borrower_management_workflow(self, admin_client):
        """Test complete borrower management workflow."""
        # 1. Create borrower
        borrower_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+255123456789',
            'email': 'john.doe@example.com',
            'national_id': 'ID12345678',
            'date_of_birth': '1990-01-01',
            'gender': 'male',
            'address': '123 Main St',
            'city': 'Dar es Salaam',
            'occupation': 'Business Owner',
        }
        
        response = admin_client.post(reverse('borrowers:add_borrower'), borrower_data)
        assert response.status_code in [200, 302]
        
        # 2. Verify borrower creation
        from apps.borrowers.models import Borrower
        borrower = Borrower.objects.filter(national_id='ID12345678').first()
        assert borrower is not None
        assert borrower.first_name == 'John'
        assert borrower.status == 'active'
        
        # 3. Update borrower
        update_data = {
            'phone_number': '+255987654321',
            'email': 'john.updated@example.com',
            'address': '456 New Street',
        }
        
        response = admin_client.post(
            reverse('borrowers:edit_borrower', args=[borrower.id]),
            {**borrower_data, **update_data}
        )
        assert response.status_code in [200, 302]
        
        # 4. Verify update
        borrower.refresh_from_db()
        assert borrower.phone_number == '+255987654321'
        assert borrower.email == 'john.updated@example.com'
    
    def test_financial_statements_workflow(self, admin_client, sample_data):
        """Test financial statements generation."""
        # 1. Access trial balance
        response = admin_client.get(reverse('financial_statements:trial_balance'))
        assert response.status_code == 200
        
        # 2. Access journal entries
        response = admin_client.get(reverse('financial_statements:runs'))
        assert response.status_code == 200
        
        # 3. Access account balances
        response = admin_client.get(reverse('financial_statements:periods'))
        assert response.status_code == 200
        
        # 4. Generate trial balance report
        report_data = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'format': 'pdf',
        }
        
        response = admin_client.post(
            reverse('financial_statements:trial_balance'),
            report_data
        )
        assert response.status_code in [200, 302]
    
    @pytest.mark.slow
    def test_system_performance(self, admin_client, performance_test_data):
        """Test system performance with large datasets."""
        import time
        
        # Test borrowers list performance
        start_time = time.time()
        response = admin_client.get(reverse('borrowers:borrower_list'))
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should load within 2 seconds
        
        # Test loans list performance
        start_time = time.time()
        response = admin_client.get(reverse('loans:loan_list'))
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should load within 2 seconds
    
    def test_user_permissions(self, client, regular_user, staff_user, admin_user):
        """Test user permission system."""
        # Test regular user access
        client.force_login(regular_user)
        
        # Should not access admin pages
        response = client.get(reverse('admin:index'))
        assert response.status_code in [302, 403]
        
        # Should not access loan creation
        response = client.get(reverse('loans:add_loan'))
        assert response.status_code in [302, 403]
        
        # Test staff user access
        client.force_login(staff_user)
        
        # Should access dashboard
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
        
        # Should access borrower list
        response = client.get(reverse('borrowers:borrower_list'))
        assert response.status_code == 200
        
        # Test admin user access
        client.force_login(admin_user)
        
        # Should access admin pages
        response = client.get(reverse('admin:index'))
        assert response.status_code == 200
        
        # Should access all system features
        response = client.get(reverse('financial_statements:dashboard'))
        assert response.status_code == 200
    
    def test_error_handling(self, admin_client):
        """Test system error handling."""
        # Test 404 error
        response = admin_client.get('/nonexistent-page/')
        assert response.status_code == 404
        
        # Test invalid form submission
        response = admin_client.post(reverse('borrowers:add_borrower'), {})
        assert response.status_code == 200  # Form validation errors
        
        # Test invalid loan amount
        invalid_loan_data = {
            'amount_requested': '-1000.00',  # Invalid negative amount
        }
        response = admin_client.post(reverse('loans:add_loan'), invalid_loan_data)
        assert response.status_code == 200  # Form validation errors
    
    def test_security_features(self, client):
        """Test security features."""
        # Test CSRF protection
        response = client.post(reverse('borrowers:add_borrower'), {})
        assert response.status_code == 403  # CSRF token missing
        
        # Test login required
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302  # Redirect to login
        
        # Test SQL injection protection
        malicious_data = {
            'search': "'; DROP TABLE borrowers_borrower; --"
        }
        response = client.get(reverse('borrowers:borrower_list'), malicious_data)
        # Should not cause server error
        assert response.status_code in [200, 302, 403]
