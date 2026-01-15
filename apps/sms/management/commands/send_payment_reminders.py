"""
Management command to send payment reminders via SMS
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.loans.models import Loan, RepaymentSchedule
from apps.core.sms_service import sms_service


class Command(BaseCommand):
    help = 'Send SMS payment reminders to borrowers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=3,
            help='Send reminders for payments due in X days (default: 3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending SMS'
        )
        parser.add_argument(
            '--overdue-only',
            action='store_true',
            help='Send reminders only for overdue payments'
        )

    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        dry_run = options['dry_run']
        overdue_only = options['overdue_only']
        
        today = timezone.now().date()
        
        if overdue_only:
            # Get overdue installments
            installments = RepaymentSchedule.objects.filter(
                due_date__lt=today,
                status__in=['pending', 'partial']
            ).select_related('loan__borrower')

            self.stdout.write(f"Found {installments.count()} overdue installments")
        else:
            # Get upcoming installments
            target_date = today + timedelta(days=days_ahead)
            installments = RepaymentSchedule.objects.filter(
                due_date=target_date,
                status__in=['pending', 'partial']
            ).select_related('loan__borrower')

            self.stdout.write(f"Found {installments.count()} installments due on {target_date}")
        
        sent_count = 0
        failed_count = 0
        
        for installment in installments:
            borrower = installment.loan.borrower
            
            if not borrower.phone_number:
                self.stdout.write(
                    self.style.WARNING(f"No phone number for {borrower.get_full_name()}")
                )
                continue
            
            if dry_run:
                self.stdout.write(
                    f"Would send reminder to {borrower.get_full_name()} ({borrower.phone_number}) "
                    f"for loan {installment.loan.loan_number}, amount Tsh {installment.amount_due}"
                )
                sent_count += 1
            else:
                try:
                    if overdue_only:
                        result = sms_service.send_overdue_reminder(installment)
                    else:
                        result = sms_service.send_payment_reminder(installment)
                    
                    if result.get('success'):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Sent reminder to {borrower.get_full_name()} ({borrower.phone_number})"
                            )
                        )
                        sent_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to send to {borrower.get_full_name()}: {result.get('error')}"
                            )
                        )
                        failed_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error sending to {borrower.get_full_name()}: {str(e)}"
                        )
                    )
                    failed_count += 1
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: Would send {sent_count} SMS reminders")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"SMS reminders sent: {sent_count} successful, {failed_count} failed"
                )
            )
            
            if not sms_service.enabled:
                self.stdout.write(
                    self.style.WARNING("SMS service is disabled - messages were logged but not sent")
                )
