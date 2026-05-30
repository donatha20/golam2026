from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed default IncomeSource and ExpenseCategory records (non-destructive)'

    def handle(self, *args, **options):
        from apps.core.models import IncomeSource, ExpenseCategory

        income_defaults = [
            ('loan_interest', 'Loan Interest', 'operational'),
            ('service_fees', 'Service Fees', 'operational'),
            ('membership_fees', 'Membership Fees', 'operational'),
            ('investment_returns', 'Investment Returns', 'investment'),
            ('donations', 'Donations', 'other'),
            ('other', 'Other Income', 'other'),
        ]

        expense_defaults = [
            ('operational', 'Operational Expenses', 'operational'),
            ('administrative', 'Administrative Expenses', 'administrative'),
            ('financial', 'Financial Expenses', 'financial'),
            ('other', 'Other Expenses', 'other'),
        ]

        created = 0
        for code, name, source_type in income_defaults:
            obj, was_created = IncomeSource.objects.get_or_create(code=code, defaults={
                'name': name,
                'source_type': source_type,
                'is_active': True,
            })
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created IncomeSource: {name}'))

        for code, name, category_type in expense_defaults:
            obj, was_created = ExpenseCategory.objects.get_or_create(code=code, defaults={
                'name': name,
                'category_type': category_type,
                'is_active': True,
            })
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created ExpenseCategory: {name}'))

        if created == 0:
            self.stdout.write('No new records created. All defaults already exist.')
        else:
            self.stdout.write(self.style.SUCCESS(f'Seeded {created} default records.'))
