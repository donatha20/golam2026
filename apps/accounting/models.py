"""
Accounting and financial records models for the microfinance system.
"""
from django.db import models
from django.utils import timezone
from decimal import Decimal
from apps.core.models import AuditModel, AccountTypeChoices
from apps.accounts.models import CustomUser


class Account(AuditModel):
    """Chart of accounts model."""
    account_code = models.CharField(max_length=20, unique=True)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=15, choices=AccountTypeChoices.choices)
    parent_account = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_accounts'
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    # Enhanced fields for financial statements
    is_system_account = models.BooleanField(default=False, help_text="System-generated account")
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    opening_balance_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['account_code']

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"

    def get_balance(self, as_of_date=None):
        """Calculate account balance as of a specific date."""
        from django.db.models import Sum

        lines = self.journalentryline_set.filter(
            journal_entry__is_posted=True
        )

        if as_of_date:
            lines = lines.filter(journal_entry__entry_date__lte=as_of_date)

        total_debits = lines.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')
        total_credits = lines.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')

        # Add opening balance
        balance = self.opening_balance

        # Calculate balance based on account type
        if self.account_type in ['asset', 'expense']:
            # Normal debit balance
            balance += total_debits - total_credits
        else:
            # Normal credit balance (liability, equity, revenue)
            balance += total_credits - total_debits

        return balance

    @property
    def current_balance(self):
        """Get current account balance."""
        return self.get_balance()

    @property
    def has_sub_accounts(self):
        """Check if account has sub-accounts."""
        return self.sub_accounts.exists()

    def get_account_hierarchy(self):
        """Get full account hierarchy path."""
        if self.parent_account:
            return f"{self.parent_account.get_account_hierarchy()} > {self.account_name}"
        return self.account_name


class JournalEntry(AuditModel):
    """Journal entry model for double-entry bookkeeping."""
    entry_number = models.CharField(max_length=20, unique=True, editable=False)
    entry_date = models.DateField()
    description = models.TextField()
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.PositiveIntegerField(blank=True, null=True)
    is_posted = models.BooleanField(default=False)

    # Enhanced fields
    is_reversing = models.BooleanField(default=False, help_text="Reversing entry")
    reversed_entry = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversing_entries'
    )
    posted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_entries'
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"{self.entry_number} - {self.description}"

    def save(self, *args, **kwargs):
        """Auto-generate entry number if not provided."""
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        super().save(*args, **kwargs)

    def generate_entry_number(self):
        """Generate unique journal entry number using sequential format: JE-0001."""
        last_entry = JournalEntry.objects.filter(
            entry_number__startswith='JE-'
        ).order_by('entry_number').last()

        if last_entry:
            last_number = int(last_entry.entry_number[3:])  # Extract digits after 'JE-'
            new_number = last_number + 1
        else:
            new_number = 1

        return f"JE-{new_number:04d}"

    @property
    def total_debits(self):
        """Calculate total debits for this entry."""
        return sum(line.debit_amount for line in self.lines.all())

    @property
    def total_credits(self):
        """Calculate total credits for this entry."""
        return sum(line.credit_amount for line in self.lines.all())

    @property
    def is_balanced(self):
        """Check if journal entry is balanced."""
        return self.total_debits == self.total_credits

    def post(self, user=None):
        """Post the journal entry."""
        if not self.is_balanced:
            raise ValueError("Cannot post unbalanced journal entry")

        self.is_posted = True
        self.posted_by = user
        self.posted_at = timezone.now()
        self.save()

    def reverse(self, user=None, description=None):
        """Create a reversing entry."""
        if not self.is_posted:
            raise ValueError("Cannot reverse unposted entry")

        reversing_description = description or f"Reversal of {self.entry_number}"

        reversing_entry = JournalEntry.objects.create(
            entry_date=timezone.now().date(),
            description=reversing_description,
            reference_type=self.reference_type,
            reference_id=self.reference_id,
            is_reversing=True,
            reversed_entry=self,
            created_by=user
        )

        # Create reversing lines (swap debits and credits)
        for line in self.lines.all():
            JournalEntryLine.objects.create(
                journal_entry=reversing_entry,
                account=line.account,
                debit_amount=line.credit_amount,
                credit_amount=line.debit_amount,
                description=f"Reversal: {line.description}"
            )

        # Post the reversing entry
        reversing_entry.post(user)

        return reversing_entry


class JournalEntryLine(models.Model):
    """Journal entry line items."""
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    description = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.account_name}"

    def clean(self):
        """Validate that either debit or credit is specified, but not both."""
        from django.core.exceptions import ValidationError

        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError("A line cannot have both debit and credit amounts.")

        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValidationError("A line must have either a debit or credit amount.")

    @property
    def amount(self):
        """Get the line amount (debit or credit)."""
        return self.debit_amount if self.debit_amount > 0 else self.credit_amount

    @property
    def is_debit(self):
        """Check if this is a debit line."""
        return self.debit_amount > 0

    @property
    def is_credit(self):
        """Check if this is a credit line."""
        return self.credit_amount > 0


