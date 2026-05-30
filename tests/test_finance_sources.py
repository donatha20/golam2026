from django.test import TestCase, Client
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.core.models import IncomeSource, ExpenseCategory
from apps.finance_tracker.models import Income, Expenditure
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class FinanceSourcesTests(TestCase):
    def setUp(self):
        # create a user
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client = Client()
        self.client.login(username='tester', password='pass')

    def test_seed_finance_sources_command(self):
        # Ensure seeder runs without error and creates defaults
        call_command('seed_finance_sources')
        self.assertTrue(IncomeSource.objects.filter(code='loan_interest').exists())
        self.assertTrue(ExpenseCategory.objects.filter(code='operational').exists())

    def test_add_income_with_configured_source(self):
        # make sure a source exists
        source = IncomeSource.objects.create(code='service_fees', name='Service Fees')

        url = reverse('finance_tracker:add_income')
        data = {
            'source': str(source.id),
            'category': '',
            'amount': '10000.00',
            'description': 'Test income from service',
            'income_date': timezone.now().date().isoformat(),
            'reference_number': 'REF123',
            'received_from': 'Client A',
            'payment_method': 'CASH',
        }

        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Income.objects.filter(recorded_by=self.user, amount='10000.00').exists())

    def test_add_expenditure_with_configured_type(self):
        category = ExpenseCategory.objects.create(code='administrative', name='Administrative Expenses')
        url = reverse('finance_tracker:add_expenditure')
        data = {
            'expenditure_type': str(category.id),
            'category': '',
            'amount': '5000.00',
            'description': 'Office supplies',
            'expenditure_date': timezone.now().date().isoformat(),
            'vendor_name': 'Stationery Shop',
            'vendor_contact': '0777123456',
            'payment_method': 'CASH',
            'reference_number': 'REF456',
            'invoice_number': '',
            'status': 'pending',
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Expenditure.objects.filter(recorded_by=self.user, amount='5000.00').exists())
