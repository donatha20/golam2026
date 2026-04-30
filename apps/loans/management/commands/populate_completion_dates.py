"""
Management command to populate completion_date for existing completed loans.
"""

from django.core.management.base import BaseCommand
from django.db.models import Max
from apps.loans.models import Loan, LoanStatusChoices
from apps.repayments.models import Payment, PaymentStatus


class Command(BaseCommand):
    help = 'Populate completion_date for existing completed loans from last payment date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        # Find all completed loans without a completion_date
        loans_to_update = Loan.objects.filter(
            status=LoanStatusChoices.COMPLETED,
            completion_date__isnull=True
        )

        count = loans_to_update.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No loans need completion_date population')
            )
            return

        for loan in loans_to_update:
            # Get last payment date for this loan
            last_payment = Payment.objects.filter(
                loan=loan,
                status=PaymentStatus.COMPLETED,
                is_reversed=False
            ).aggregate(
                last_date=Max('payment_date')
            )
            
            completion_date = last_payment['last_date']

            if completion_date:
                self.stdout.write(
                    f'\nLoan: {loan.loan_number} (ID: {loan.id})'
                )
                self.stdout.write(
                    f'  Last payment date: {completion_date}'
                )

                if not dry_run:
                    loan.completion_date = completion_date
                    loan.save(update_fields=['completion_date'])
                    self.stdout.write(self.style.SUCCESS('  ✓ Updated'))
                else:
                    self.stdout.write(self.style.WARNING('  [DRY RUN - NOT SAVED]'))
            else:
                self.stdout.write(
                    f'\nLoan: {loan.loan_number} - No payments found'
                )

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n✓ COMPLETION_DATE POPULATION COMPLETE\n'))
        self.stdout.write(f'Loans processed: {count}')

        if dry_run:
            self.stdout.write(
                '\n' + self.style.WARNING('[DRY RUN MODE - No changes were saved]')
            )
