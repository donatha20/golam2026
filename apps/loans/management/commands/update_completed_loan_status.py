"""
Management command to update loan status to COMPLETED for loans with zero outstanding balance.
"""

from django.core.management.base import BaseCommand
from apps.loans.models import Loan, LoanStatusChoices


class Command(BaseCommand):
    help = 'Update loan status to COMPLETED for loans with zero outstanding balance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        # Find all loans with zero outstanding balance that are not already COMPLETED
        loans_to_update = Loan.objects.filter(
            outstanding_balance=0
        ).exclude(
            status=LoanStatusChoices.COMPLETED
        )

        count = loans_to_update.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No loans need status update')
            )
            return

        for loan in loans_to_update:
            self.stdout.write(
                f'\nLoan: {loan.loan_number} (ID: {loan.id})'
            )
            self.stdout.write(
                f'  Current status: {loan.get_status_display()}'
            )
            self.stdout.write(
                f'  Outstanding: Tsh {loan.outstanding_balance:,.2f}'
            )
            self.stdout.write(
                f'  → New status: {LoanStatusChoices.COMPLETED}'
            )

            if not dry_run:
                loan.status = LoanStatusChoices.COMPLETED
                loan.save(update_fields=['status'])
                self.stdout.write(self.style.SUCCESS('  ✓ Updated'))
            else:
                self.stdout.write(self.style.WARNING('  [DRY RUN - NOT SAVED]'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n✓ STATUS UPDATE COMPLETE\n'))
        self.stdout.write(f'Loans updated: {count}')

        if dry_run:
            self.stdout.write(
                '\n' + self.style.WARNING('[DRY RUN MODE - No changes were saved]')
            )
