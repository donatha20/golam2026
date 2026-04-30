"""
Management command to set up sample data for testing the microfinance system.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from apps.accounts.models import CustomUser, Branch, UserRole
from apps.borrowers.models import Borrower
from apps.savings.models import SavingsProduct


class Command(BaseCommand):
    help = 'Set up sample data for testing the microfinance system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up sample data...'))

        # Create a branch
        branch, created = Branch.objects.get_or_create(
            name="Main Branch",
            defaults={
                'code': 'MB001',
                'address': 'Nanenane, Morogoro, Tanzania',
                'phone_number': '+255747513065',
                'email': 'main@golamfinancial.co.tz'
            }
        )
        self.stdout.write(f"Branch {'created' if created else 'exists'}: {branch}")

        # Create savings products
        savings_products_data = [
            {
                'name': 'Basic Savings',
                'description': 'Basic savings account for all customers',
                'interest_rate': Decimal('5.00'),
                'minimum_opening_balance': Decimal('50000'),
                'minimum_balance': Decimal('10000'),
                'minimum_deposit': Decimal('5000')
            },
            {
                'name': 'Premium Savings',
                'description': 'High-yield savings account',
                'interest_rate': Decimal('8.00'),
                'minimum_opening_balance': Decimal('200000'),
                'minimum_balance': Decimal('50000'),
                'minimum_deposit': Decimal('10000')
            }
        ]

        for savings_data in savings_products_data:
            savings_product, created = SavingsProduct.objects.get_or_create(
                name=savings_data['name'],
                defaults=savings_data
            )
            self.stdout.write(f"Savings product {'created' if created else 'exists'}: {savings_product}")

        # Create a loan officer user
        admin_user = CustomUser.objects.filter(username='admin').first()
        if admin_user:
            admin_user.branch = branch
            admin_user.save()
            self.stdout.write(f"Updated admin user with branch: {branch}")

        loan_officer, created = CustomUser.objects.get_or_create(
            username='officer1',
            defaults={
                'email': 'officer1@golamfinancial.co.tz',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': UserRole.LOAN_OFFICER,
                'branch': branch,
                'is_active': True,
                'phone_number': '+255747513066'
            }
        )
        if created:
            loan_officer.set_password('officer123')
            loan_officer.save()
        self.stdout.write(f"Loan officer {'created' if created else 'exists'}: {loan_officer}")

        # Create sample borrowers
        borrowers_data = [
            {
                'first_name': 'Maria',
                'last_name': 'Mwalimu',
                'gender': 'female',
                'date_of_birth': '1985-03-15',
                'marital_status': 'married',
                'occupation': 'Small Business Owner',
                'phone_number': '+255747513067',
                'id_type': 'national_id',
                'id_number': 'ID001234567',
                'street': 'Sokoine Road',
                'ward': 'Nanenane',
                'district': 'Morogoro Urban',
                'region': 'Morogoro',
                'next_of_kin_name': 'Joseph Mwalimu',
                'next_of_kin_relationship': 'Husband',
                'next_of_kin_phone': '+255747513068',
                'next_of_kin_address': 'Same as borrower'
            },
            {
                'first_name': 'Hassan',
                'last_name': 'Mwanga',
                'gender': 'male',
                'date_of_birth': '1978-08-22',
                'marital_status': 'single',
                'occupation': 'Farmer',
                'phone_number': '+255747513069',
                'id_type': 'national_id',
                'id_number': 'ID001234568',
                'street': 'Mazimbu Road',
                'ward': 'Mazimbu',
                'district': 'Morogoro Urban',
                'region': 'Morogoro',
                'next_of_kin_name': 'Fatuma Mwanga',
                'next_of_kin_relationship': 'Sister',
                'next_of_kin_phone': '+255747513070',
                'next_of_kin_address': 'Mazimbu, Morogoro'
            }
        ]

        for borrower_data in borrowers_data:
            borrower, created = Borrower.objects.get_or_create(
                id_number=borrower_data['id_number'],
                defaults={
                    **borrower_data,
                    'branch': branch,
                    'registered_by': admin_user or loan_officer,
                    'registration_date': timezone.now().date()
                }
            )
            self.stdout.write(f"Borrower {'created' if created else 'exists'}: {borrower}")

        self.stdout.write(
            self.style.SUCCESS('Sample data setup completed successfully!')
        )
        self.stdout.write(
            self.style.WARNING('Login credentials:')
        )
        self.stdout.write('Admin: username=admin, password=admin123')
        self.stdout.write('Loan Officer: username=officer1, password=officer123')


