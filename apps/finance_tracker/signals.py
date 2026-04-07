"""
Django signals for finance tracker app.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Income, Expenditure
from .services import create_income_journal_entry, create_expenditure_journal_entry
from apps.accounting.models import JournalEntry


@receiver(post_save, sender=Income)
def create_income_journal_entry_signal(sender, instance, created, **kwargs):
    """
    Create journal entry when income is created.
    Only create journal entry for new income records.
    """
    if created:
        # Use transaction.on_commit to ensure the income is saved first
        transaction.on_commit(
            lambda: create_income_journal_entry(instance)
        )


@receiver(post_save, sender=Expenditure)
def create_expenditure_journal_entry_signal(sender, instance, created, **kwargs):
    """
    Create journal entry when expenditure is created and approved.
    Only create journal entry for new expenditure records that are approved or paid.
    """
    if created and instance.status in ['approved', 'paid']:
        # Use transaction.on_commit to ensure the expenditure is saved first
        transaction.on_commit(
            lambda: create_expenditure_journal_entry(instance)
        )
    elif not created and instance.status in ['approved', 'paid']:
        # Handle status change to approved/paid
        # Check if journal entry already exists
        existing_entry = JournalEntry.objects.filter(
            reference_type='Expenditure',
            reference_id=instance.id
        ).first()
        
        if not existing_entry:
            transaction.on_commit(
                lambda: create_expenditure_journal_entry(instance)
            )


@receiver(post_delete, sender=Income)
def delete_income_journal_entry_signal(sender, instance, **kwargs):
    """
    Delete related journal entry when income is deleted.
    """
    try:
        journal_entry = JournalEntry.objects.get(
            reference_type='Income',
            reference_id=instance.id
        )
        journal_entry.delete()
    except JournalEntry.DoesNotExist:
        pass


@receiver(post_delete, sender=Expenditure)
def delete_expenditure_journal_entry_signal(sender, instance, **kwargs):
    """
    Delete related journal entry when expenditure is deleted.
    """
    try:
        journal_entry = JournalEntry.objects.get(
            reference_type='Expenditure',
            reference_id=instance.id
        )
        journal_entry.delete()
    except JournalEntry.DoesNotExist:
        pass


