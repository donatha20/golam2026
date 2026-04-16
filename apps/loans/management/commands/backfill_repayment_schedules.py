from django.core.management.base import BaseCommand

from apps.core.models import LoanStatusChoices
from apps.loans.models import Loan


class Command(BaseCommand):
    help = "Generate missing repayment schedules for already disbursed loans."

    def handle(self, *args, **options):
        disbursed_loans = Loan.objects.filter(status=LoanStatusChoices.DISBURSED)

        fixed = 0
        skipped = 0

        for loan in disbursed_loans:
            if not loan.disbursement_date:
                skipped += 1
                continue

            if loan.repayment_schedules.exists():
                skipped += 1
                continue

            loan.generate_repayment_schedule()
            fixed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill completed. Created schedules for {fixed} loans; skipped {skipped}."
            )
        )
