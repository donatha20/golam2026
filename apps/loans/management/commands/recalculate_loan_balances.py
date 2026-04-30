"""
Management command to recalculate all loan outstanding balances based on payments.

This command fixes any existing loans where outstanding_balance was incorrectly
calculated. It recalculates:
- total_paid: sum of all non-reversed COMPLETED payments
- outstanding_balance: total_amount - total_paid
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from decimal import Decimal
from apps.loans.models import Loan
from apps.repayments.models import Payment, PaymentStatus


class Command(BaseCommand):
    help = 'Recalculate all loan outstanding balances based on actual payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--loan-id',
            type=int,
            help='Recalculate a specific loan by ID',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        loan_id = options.get('loan_id')

        # Get loans to process
        if loan_id:
            loans = Loan.objects.filter(id=loan_id)
            if not loans.exists():
                self.stdout.write(
                    self.style.ERROR(f'Loan with ID {loan_id} not found')
                )
                return
        else:
            loans = Loan.objects.all()

        total_loans = loans.count()
        updated_count = 0
        error_count = 0
        unchanged_count = 0

        self.stdout.write(
            self.style.SUCCESS(f'Processing {total_loans} loans...\n')
        )

        for loan in loans:
            try:
                # Calculate actual paid amount from non-reversed completed payments
                total_paid_result = Payment.objects.filter(
                    loan=loan,
                    status=PaymentStatus.COMPLETED,
                    is_reversed=False
                ).aggregate(
                    total=Sum('amount')
                )
                total_paid = total_paid_result['total'] or Decimal('0.00')

                # Calculate new outstanding balance
                new_outstanding = loan.total_amount - total_paid
                if new_outstanding < 0:
                    new_outstanding = Decimal('0.00')

                # Check if values have changed
                old_total_paid = loan.total_paid
                old_outstanding = loan.outstanding_balance

                if old_total_paid != total_paid or old_outstanding != new_outstanding:
                    self.stdout.write(
                        f'\nLoan: {loan.loan_number} (ID: {loan.id})'
                    )
                    self.stdout.write(f'  Total Amount: Tsh {loan.total_amount:,.2f}')
                    self.stdout.write(
                        f'  Old total_paid: Tsh {old_total_paid:,.2f} → '
                        f'New: Tsh {total_paid:,.2f}'
                    )
                    self.stdout.write(
                        f'  Old outstanding: Tsh {old_outstanding:,.2f} → '
                        f'New: Tsh {new_outstanding:,.2f}'
                    )

                    if not dry_run:
                        loan.total_paid = total_paid
                        loan.outstanding_balance = new_outstanding
                        loan.save(
                            update_fields=['total_paid', 'outstanding_balance']
                        )
                        self.stdout.write(self.style.SUCCESS('  ✓ Updated'))
                    else:
                        self.stdout.write(self.style.WARNING('  [DRY RUN - NOT SAVED]'))

                    updated_count += 1
                else:
                    unchanged_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'\nError processing loan {loan.loan_number}: {str(e)}'
                    )
                )
                error_count += 1

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n✓ RECALCULATION COMPLETE\n'))
        self.stdout.write(f'Total loans processed: {total_loans}')
        self.stdout.write(
            self.style.SUCCESS(f'Updated: {updated_count}')
        )
        self.stdout.write(
            self.style.WARNING(f'Unchanged: {unchanged_count}')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'Errors: {error_count}')
            )

        if dry_run:
            self.stdout.write(
                '\n' + self.style.WARNING('[DRY RUN MODE - No changes were saved]')
            )
