"""
Signals for the payroll app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Employee, PayrollRecord, SalaryAdvance


@receiver(post_save, sender=Employee)
def employee_post_save(sender, instance, created, **kwargs):
    """Handle employee post-save operations."""
    if created:
        # Log employee creation
        print(f"New employee created: {instance.get_full_name()}")


@receiver(pre_save, sender=PayrollRecord)
def payroll_record_pre_save(sender, instance, **kwargs):
    """Handle payroll record pre-save operations."""
    # Ensure calculation date is set when status changes to calculated
    if instance.status == 'calculated' and not instance.calculation_date:
        instance.calculation_date = timezone.now()


@receiver(post_save, sender=SalaryAdvance)
def salary_advance_post_save(sender, instance, created, **kwargs):
    """Handle salary advance post-save operations."""
    if created:
        # Log advance creation
        print(f"New salary advance created: {instance.advance_number}")
        
    # Set remaining balance when approved
    if instance.status == 'approved' and not instance.remaining_balance:
        instance.remaining_balance = instance.amount
        # Use update to avoid recursion
        SalaryAdvance.objects.filter(id=instance.id).update(
            remaining_balance=instance.amount
        )
