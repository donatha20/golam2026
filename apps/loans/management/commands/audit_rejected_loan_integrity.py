from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import LoanStatusChoices
from apps.loans.models import Loan


class Command(BaseCommand):
    help = (
        "Audit rejected loans for disbursement artifacts. "
        "Use --fix to clear only safe artifacts when no real payments exist."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Apply safe fixes for rejected loans without payment activity.",
        )

    def handle(self, *args, **options):
        apply_fix = options["fix"]

        rejected_loans = Loan.objects.filter(status=LoanStatusChoices.REJECTED).select_related("borrower")

        total_rejected = rejected_loans.count()
        affected = 0
        fixed = 0
        blocked = 0

        self.stdout.write(self.style.NOTICE(f"Rejected loans scanned: {total_rejected}"))

        for loan in rejected_loans:
            has_disbursement_record = loan.disbursements.exists()
            has_disbursement_fields = bool(loan.disbursement_date or loan.disbursed_by_id or loan.maturity_date)
            has_schedule_rows = loan.repayment_schedules.exists()
            has_legacy_repayments = loan.repayment_schedules.filter(repayments__isnull=False).exists()
            has_payments = loan.payments.exists()

            has_issue = any([
                has_disbursement_record,
                has_disbursement_fields,
                has_schedule_rows,
            ])

            if not has_issue:
                continue

            affected += 1
            unsafe_to_fix = has_legacy_repayments or has_payments

            self.stdout.write(
                f"- {loan.loan_number}: artifacts found "
                f"(records={has_disbursement_record}, fields={has_disbursement_fields}, schedules={has_schedule_rows}, "
                f"payments={has_payments}, legacy_repayments={has_legacy_repayments})"
            )

            if not apply_fix:
                continue

            if unsafe_to_fix:
                blocked += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipped {loan.loan_number}: linked payment activity detected; manual review required."
                    )
                )
                continue

            with transaction.atomic():
                loan.disbursements.all().delete()
                loan.repayment_schedules.all().delete()
                loan.disbursement_date = None
                loan.maturity_date = None
                loan.disbursed_by = None
                loan.save(update_fields=["disbursement_date", "maturity_date", "disbursed_by", "updated_at"])

            fixed += 1
            self.stdout.write(self.style.SUCCESS(f"  Fixed {loan.loan_number}"))

        summary = (
            f"Summary: scanned={total_rejected}, affected={affected}, "
            f"fixed={fixed}, blocked={blocked}, dry_run={not apply_fix}"
        )
        self.stdout.write(self.style.SUCCESS(summary))
