"""
Management command to safely correct legacy manual-interest drift records.

Example drift:
- Expected: total_interest=2300.00, total_amount=21300.00
- Stored:   total_interest=2299.95, total_amount=21299.95

The command is dry-run by default and only applies updates when --apply is provided.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.loans.models import Loan


class Command(BaseCommand):
    help = (
        "Detect and correct legacy manual-interest drift records "
        "(dry-run by default)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--loan-id",
            dest="loan_ids",
            type=int,
            action="append",
            help="Specific loan ID to inspect/fix. Can be provided multiple times.",
        )
        parser.add_argument(
            "--auto-detect",
            action="store_true",
            help="Scan all loans and detect conservative drift candidates.",
        )
        parser.add_argument(
            "--include-paid",
            action="store_true",
            help="Also include loans that already have repayments (safer to keep this off).",
        )
        parser.add_argument(
            "--max-delta",
            default="0.05",
            help="Maximum allowed correction delta in interest (default: 0.05).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist updates. Without this flag, command runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        loan_ids = options.get("loan_ids") or []
        auto_detect = options.get("auto_detect", False)
        include_paid = options.get("include_paid", False)
        apply_updates = options.get("apply", False)

        if not loan_ids and not auto_detect:
            raise CommandError("Provide --loan-id or use --auto-detect.")

        max_delta = self._to_money(options.get("max_delta", "0.05"))
        if max_delta <= Decimal("0.00"):
            raise CommandError("--max-delta must be greater than 0.")

        queryset = Loan.objects.all().order_by("id")
        if loan_ids:
            queryset = queryset.filter(id__in=loan_ids)
            found_ids = set(queryset.values_list("id", flat=True))
            missing_ids = [loan_id for loan_id in loan_ids if loan_id not in found_ids]
            if missing_ids:
                raise CommandError(f"Loan IDs not found: {missing_ids}")

        candidates = []
        skipped = 0

        for loan in queryset.iterator():
            candidate = self._build_candidate(
                loan=loan,
                include_paid=include_paid,
                max_delta=max_delta,
            )
            if candidate:
                candidates.append(candidate)
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS("\nDetected drift candidates:"))
        if not candidates:
            self.stdout.write(self.style.WARNING("  None found."))
            self.stdout.write(f"Scanned: {queryset.count()} | Skipped: {skipped}")
            return

        for item in candidates:
            loan = item["loan"]
            self.stdout.write(
                f"\nLoan {loan.loan_number} (ID: {loan.id})"
            )
            self.stdout.write(
                f"  Interest: {item['old_interest']} -> {item['new_interest']} "
                f"(delta {item['delta']:+.2f})"
            )
            self.stdout.write(
                f"  Total:    {item['old_total']} -> {item['new_total']}"
            )
            self.stdout.write(
                f"  Balance:  {item['old_balance']} -> {item['new_balance']}"
            )
            if item["loan"].total_paid > Decimal("0.00"):
                self.stdout.write("  Note: Loan has payments recorded.")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: scanned={queryset.count()} candidates={len(candidates)} skipped={skipped}"
            )
        )

        if not apply_updates:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --apply to persist."))
            return

        updated = 0
        with transaction.atomic():
            for item in candidates:
                loan = item["loan"]
                Loan.objects.filter(pk=loan.pk).update(
                    total_interest=item["new_interest"],
                    total_amount=item["new_total"],
                    outstanding_balance=item["new_balance"],
                )
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Applied updates to {updated} loan(s)."))

    def _build_candidate(self, loan, include_paid, max_delta):
        principal = self._to_money(loan.amount_approved)
        rate = self._to_money(loan.interest_rate)
        months = Decimal(str(loan.duration_months or 0))
        total_interest = self._to_money(loan.total_interest)
        total_amount = self._to_money(loan.total_amount)
        total_paid = self._to_money(loan.total_paid)

        if principal <= Decimal("0.00") or rate <= Decimal("0.00") or months <= Decimal("0"):
            return None

        if not include_paid and total_paid > Decimal("0.00"):
            return None

        # Conservative fingerprint for affected records:
        # 1) Current interest matches formula from rounded interest_rate.
        # 2) Current total is principal + current interest.
        derived_interest = (
            principal * (rate / Decimal("100")) * (months / Decimal("12"))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if total_interest != derived_interest:
            return None

        if total_amount != (principal + total_interest).quantize(Decimal("0.01")):
            return None

        # Proposed correction: nearest whole-currency manual interest amount.
        corrected_interest = total_interest.quantize(Decimal("1"), rounding=ROUND_HALF_UP).quantize(
            Decimal("0.01")
        )
        delta = (corrected_interest - total_interest).quantize(Decimal("0.01"))

        if delta == Decimal("0.00"):
            return None
        if abs(delta) > max_delta:
            return None

        corrected_total = (principal + corrected_interest).quantize(Decimal("0.01"))
        corrected_balance = (corrected_total - total_paid).quantize(Decimal("0.01"))
        if corrected_balance < Decimal("0.00"):
            corrected_balance = Decimal("0.00")

        return {
            "loan": loan,
            "old_interest": total_interest,
            "new_interest": corrected_interest,
            "delta": delta,
            "old_total": total_amount,
            "new_total": corrected_total,
            "old_balance": self._to_money(loan.outstanding_balance),
            "new_balance": corrected_balance,
        }

    @staticmethod
    def _to_money(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
