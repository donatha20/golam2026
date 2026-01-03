"""
Django signals for financial statements app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.accounting.models import JournalEntry
from .models import AccountingPeriod


@receiver(pre_save, sender=JournalEntry)
def validate_journal_entry_period(sender, instance, **kwargs):
    """
    Validate that journal entries are posted to open periods only.
    """
    if instance.entry_date:
        # Find the period for this entry date
        period = AccountingPeriod.objects.filter(
            start_date__lte=instance.entry_date,
            end_date__gte=instance.entry_date
        ).first()
        
        if period and not period.can_post_entries():
            raise ValueError(f'Cannot post entries to {period.get_status_display().lower()} period: {period.name}')


@receiver(post_save, sender=AccountingPeriod)
def period_status_change_notification(sender, instance, created, **kwargs):
    """
    Handle period status changes.
    """
    if not created:
        # Check if status changed to closed
        if instance.status == 'closed' and instance.closed_at:
            # Could send notifications, generate closing reports, etc.
            pass
