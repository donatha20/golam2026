#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.loans.models import Loan
from apps.core.models import FrequencyChoices

# Check the disbursed loan
loan = Loan.objects.get(loan_number='LN202607962013')

print(f"\nLoan {loan.loan_number}:")
print(f"  repayment_frequency value: {loan.repayment_frequency}")
print(f"  Display: {loan.get_repayment_frequency_display()}")
print(f"\nAll Frequency Choices:")
for code, label in FrequencyChoices.choices:
    print(f"  {code}: {label}")
